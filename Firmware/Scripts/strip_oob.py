import sys

page_data  = 2048
page_oob   = 64
page_total = page_data + page_oob

with open(sys.argv[1], 'rb') as fin, open(sys.argv[2], 'wb') as fout:
    while True:
        page = fin.read(page_total)
        if not page:
            break
        fout.write(page[:page_data])
print('Done')
