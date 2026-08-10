#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>
#include <unistd.h>
#include <sys/wait.h>
#include <sys/types.h>
#include <fcntl.h>
#include <signal.h>
#include <ctype.h>
#include <openssl/aes.h>
#include <openssl/md5.h>
#include <openssl/evp.h>
#include <zlib.h>

static const char *HEADER_LINES[5] = {
    "FW Version:", "FW Description:", "FW Create Time:", "FW Group:", "Board S/N:",
};
#define NUM_HEADERS 5

static unsigned char target_block0[16];
static unsigned char *full_ciphertext = NULL;
static size_t full_ciphertext_len = 0;
static unsigned int declared_len = 0;
static unsigned char handle_md5[16];

static void die(const char *msg) {
    fprintf(stderr, "error: %s\n", msg);
    exit(1);
}

#define RAND_DEG 31
#define RAND_SEP 3

typedef struct {
    int32_t table[RAND_DEG];
    int fptr, rptr;
} fast_rand_state;

static void fast_srand(fast_rand_state *st, unsigned int seed) {
    if (seed == 0) seed = 1;
    int32_t word = (int32_t)seed;
    st->table[0] = word;
    for (int i = 1; i < RAND_DEG; i++) {
        long hi = word / 127773;
        long lo = word % 127773;
        word = 16807 * lo - 2836 * hi;
        if (word < 0) word += 2147483647;
        st->table[i] = word;
    }
    st->fptr = RAND_SEP;
    st->rptr = 0;
    for (int i = 0; i < RAND_DEG * 10; i++) {
        st->table[st->fptr] += st->table[st->rptr];
        if (++st->fptr >= RAND_DEG) st->fptr = 0;
        if (++st->rptr >= RAND_DEG) st->rptr = 0;
    }
}

static inline int32_t fast_rand(fast_rand_state *st) {
    st->table[st->fptr] += st->table[st->rptr];
    int32_t result = (int32_t)(((uint32_t)st->table[st->fptr]) >> 1);
    if (++st->fptr >= RAND_DEG) st->fptr = 0;
    if (++st->rptr >= RAND_DEG) st->rptr = 0;
    return result;
}

static int read_file_all(const char *path, unsigned char **buf_out, size_t *len_out) {
    FILE *f = fopen(path, "rb");
    if (!f) return -1;
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    if (sz < 0) { fclose(f); return -1; }
    unsigned char *buf = malloc((size_t)sz);
    if (!buf) { fclose(f); return -1; }
    size_t got = fread(buf, 1, (size_t)sz, f);
    fclose(f);
    if (got != (size_t)sz) { free(buf); return -1; }
    *buf_out = buf;
    *len_out = (size_t)sz;
    return 0;
}

static int base64_decode(const char *in, size_t in_len, unsigned char **out, size_t *out_len) {
    char *clean = malloc(in_len + 1);
    size_t clen = 0;
    for (size_t i = 0; i < in_len; i++) {
        if (!isspace((unsigned char)in[i])) clean[clen++] = in[i];
    }
    clean[clen] = '\0';

    int pad = 0;
    if (clen >= 1 && clean[clen - 1] == '=') pad++;
    if (clen >= 2 && clean[clen - 2] == '=') pad++;
    if (clen % 4 != 0) { free(clean); return -1; }

    unsigned char *decoded = malloc((clen / 4) * 3 + 1);
    int dec_len = EVP_DecodeBlock(decoded, (const unsigned char *)clean, (int)clen);
    free(clean);
    if (dec_len < 0) { free(decoded); return -1; }

    dec_len -= pad;
    *out = decoded;
    *out_len = (size_t)dec_len;
    return 0;
}

static void parse_cfg_container(const char *path, unsigned char **der_out, size_t *der_len_out) {
    unsigned char *raw;
    size_t raw_len;
    if (read_file_all(path, &raw, &raw_len) != 0) die("could not read cfg file");

    size_t pos = 0;
    for (int i = 0; i < NUM_HEADERS; i++) {
        size_t line_start = pos;
        while (pos < raw_len && raw[pos] != '\n') pos++;
        if (pos < raw_len) pos++;
        size_t line_len = pos - line_start;
        if (line_len == 0 ||
            memmem(raw + line_start, line_len, HEADER_LINES[i], strlen(HEADER_LINES[i])) == NULL) {
            die("missing/out-of-order header line in cfg file");
        }
    }

    unsigned char *der;
    size_t der_len;
    if (base64_decode((const char *)(raw + pos), raw_len - pos, &der, &der_len) != 0) {
        free(raw);
        die("failed to base64-decode PKCS7 body");
    }
    free(raw);
    *der_out = der;
    *der_len_out = der_len;
}

static int run_openssl_extract(const char *subcmd, const char *in_path, const char *out_path) {
    pid_t pid = fork();
    if (pid < 0) die("fork failed");
    if (pid == 0) {
        int devnull = open("/dev/null", O_WRONLY);
        if (devnull >= 0) { dup2(devnull, STDERR_FILENO); dup2(devnull, STDOUT_FILENO); }
        execlp("openssl", "openssl", subcmd, "-verify", "-noverify",
               "-inform", "DER", "-in", in_path, "-out", out_path, (char *)NULL);
        _exit(127);
    }
    int status;
    waitpid(pid, &status, 0);
    return (WIFEXITED(status) && WEXITSTATUS(status) == 0) ? 0 : -1;
}

static void extract_pkcs7_content(const unsigned char *der, size_t der_len,
                                   unsigned char **content_out, size_t *content_len_out) {
    char in_path[] = "/tmp/find_cfg_key_in_XXXXXX";
    char out_path[] = "/tmp/find_cfg_key_out_XXXXXX";

    int fd_in = mkstemp(in_path);
    if (fd_in < 0) die("mkstemp failed");
    write(fd_in, der, der_len);
    close(fd_in);

    int fd_out = mkstemp(out_path);
    if (fd_out < 0) die("mkstemp failed");
    close(fd_out);
    unlink(out_path);

    int ok = run_openssl_extract("smime", in_path, out_path);
    if (ok != 0) ok = run_openssl_extract("cms", in_path, out_path);
    unlink(in_path);
    if (ok != 0) { unlink(out_path); die("openssl could not extract PKCS7 content"); }

    unsigned char *content;
    size_t content_len;
    if (read_file_all(out_path, &content, &content_len) != 0) {
        unlink(out_path);
        die("could not read openssl output");
    }
    unlink(out_path);
    *content_out = content;
    *content_len_out = content_len;
}

static void split_content(const unsigned char *content, size_t content_len,
                           unsigned int *declared_len_out,
                           unsigned char **ciphertext_out, size_t *ciphertext_len_out) {
    if (content_len < 4) die("PKCS7 content too short");
    unsigned int dl;
    memcpy(&dl, content, 4);
    *declared_len_out = dl;

    size_t ct_len = content_len - 4;
    unsigned char *ct = malloc(ct_len);
    memcpy(ct, content + 4, ct_len);
    *ciphertext_out = ct;
    *ciphertext_len_out = ct_len;
}

static void get_password(unsigned char *handle32) {
    char buf[256];
    printf("password: ");
    fflush(stdout);
    if (!fgets(buf, sizeof(buf), stdin)) die("failed to read password");

    int len = (int)strlen(buf);
    while (len > 0 && (buf[len - 1] == '\n' || buf[len - 1] == '\r')) buf[--len] = '\0';
    if (len == 0) die("empty password");
    if (len > 32) len = 32;

    memset(handle32, 0, 32);
    memcpy(handle32, buf, len);
}

static void evp_bytes_to_key_md5(const unsigned char *password, int password_len,
                                  const unsigned char *salt, unsigned char *key, unsigned char *iv) {
    unsigned char material[48];
    unsigned char prev[16];
    int material_len = 0, prev_len = 0;
    while (material_len < 48) {
        MD5_CTX mdctx;
        MD5_Init(&mdctx);
        MD5_Update(&mdctx, prev, prev_len);
        MD5_Update(&mdctx, password, password_len);
        MD5_Update(&mdctx, salt, 8);
        MD5_Final(prev, &mdctx);
        memcpy(material + material_len, prev, 16);
        material_len += 16;
        prev_len = 16;
    }
    memcpy(key, material, 32);
    memcpy(iv, material + 32, 16);
}

/* extra salt byte fixed at 0x00 -- confirmed, no longer searched. */
static inline void gen_salt8_fast(fast_rand_state *st, unsigned int seed, unsigned char *salt8) {
    fast_srand(st, seed);
    int count = 0;
    while (count < 7) {
        int32_t r = fast_rand(st);
        unsigned char c = (unsigned char)(r % 0x7f);
        if ((c >= '0' && c <= '9') || (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z')) {
            salt8[count++] = c;
        }
    }
    salt8[7] = 0x00;
}

static int check_seed(fast_rand_state *st, unsigned long seed,
                       unsigned char *out_device_key, unsigned char *out_device_iv) {
    unsigned char salt8[8];
    gen_salt8_fast(st, (unsigned int)seed, salt8);

    unsigned char device_key[32], device_iv[16], aes_key[32], key_part2[16], plain_block0[16];
    evp_bytes_to_key_md5((const unsigned char *)"secret", 6, salt8, device_key, device_iv);

    MD5(device_key, 32, key_part2);
    memcpy(aes_key, handle_md5, 16);
    memcpy(aes_key + 16, key_part2, 16);

    AES_KEY aes_ctx;
    AES_set_decrypt_key(aes_key, 256, &aes_ctx);
    AES_decrypt(target_block0, plain_block0, &aes_ctx);
    for (int i = 0; i < 16; i++) plain_block0[i] ^= device_iv[i];

    if (plain_block0[0] != 0x78 ||
        (plain_block0[1] != 0x01 && plain_block0[1] != 0x5E &&
         plain_block0[1] != 0x9C && plain_block0[1] != 0xDA)) {
        return 0;
    }

    unsigned char iv_snapshot[16];
    memcpy(iv_snapshot, device_iv, 16);

    size_t block_aligned = (full_ciphertext_len / 16) * 16;
    unsigned char *plain = malloc(block_aligned);
    AES_cbc_encrypt(full_ciphertext, plain, block_aligned, &aes_ctx, device_iv, AES_DECRYPT);

    unsigned long dest_len = declared_len;
    unsigned char *xml_out = malloc(declared_len);
    int ret = uncompress(xml_out, &dest_len, plain, block_aligned);
    free(plain);
    free(xml_out);

    if (ret == Z_OK && dest_len == declared_len) {
        memcpy(out_device_key, device_key, 32);
        memcpy(out_device_iv, iv_snapshot, 16);
        return 1;
    }
    return 0;
}

static void crack_range(unsigned long start, unsigned long end) {
    fast_rand_state st;
    unsigned char device_key[32], device_iv[16];
    for (unsigned long seed = start; seed < end; seed++) {
        if (check_seed(&st, seed, device_key, device_iv)) {
            printf("\nseed: %lu\n", seed);
            printf("private key: ");
            for (int i = 0; i < 32; i++) printf("%02x", device_key[i]);
            printf("\niv: ");
            for (int i = 0; i < 16; i++) printf("%02x", device_iv[i]);
            printf("\n");
            fflush(stdout);
            exit(0);
        }
    }
    exit(1);
}

int main(int argc, char **argv) {
    const char *cfg_path = argv[1];

    unsigned char *der;
    size_t der_len;
    parse_cfg_container(cfg_path, &der, &der_len);

    unsigned char *content;
    size_t content_len;
    extract_pkcs7_content(der, der_len, &content, &content_len);
    free(der);

    unsigned char *ciphertext;
    size_t ciphertext_len;
    split_content(content, content_len, &declared_len, &ciphertext, &ciphertext_len);
    free(content);
    if (ciphertext_len < 16) die("ciphertext too short");

    full_ciphertext = ciphertext;
    full_ciphertext_len = ciphertext_len;
    memcpy(target_block0, full_ciphertext, 16);

    unsigned char handle32[32];
    get_password(handle32);
    MD5(handle32, 32, handle_md5);

    int num_procs = (int)sysconf(_SC_NPROCESSORS_ONLN);
    if (num_procs < 1) num_procs = 1;
    unsigned long total_seeds = 0x100000000UL;
    unsigned long chunk = total_seeds / (unsigned long)num_procs;

    printf("searching (%d processes)...\n", num_procs);
    fflush(stdout);

    pid_t *pids = malloc(sizeof(pid_t) * num_procs);
    for (int i = 0; i < num_procs; i++) {
        pids[i] = fork();
        if (pids[i] == 0) {
            unsigned long start = (unsigned long)i * chunk;
            unsigned long end = (i == num_procs - 1) ? total_seeds : (unsigned long)(i + 1) * chunk;
            crack_range(start, end);
        }
    }

    int found = 0, status;
    pid_t wpid;
    while ((wpid = wait(&status)) > 0) {
        if (WIFEXITED(status) && WEXITSTATUS(status) == 0) {
            found = 1;
            for (int i = 0; i < num_procs; i++) kill(pids[i], SIGTERM);
            break;
        }
    }
    free(pids);

    if (!found) { printf("no match found.\n"); return 1; }
    return 0;
}
