// ==UserScript==
// @name         SERCOMM Reveal Hidden Settings
// @match        http://192.168.2.1/*
// @run-at       document-start
// @grant        none
// @author       Samantas5855
// ==/UserScript==
(function () {
  const TARGET_PATH = '/data/user_data.json';

  const CHANGES = {
    usermode: 'admin',
    openmodem_subpages_status: '1'
  };

  const isTarget = (url) => {
    try { return new URL(url, location.href).pathname === TARGET_PATH; }
    catch { return false; }
  };

  function applyPatch(data, changes) {
    const applied = [];
    if (Array.isArray(data)) {
      for (const item of data) {
        if (!item || typeof item !== 'object') continue;
        for (const field in changes) {
          if (Object.prototype.hasOwnProperty.call(item, field)) {
            item[field] = changes[field];
            applied.push(field);
          }
        }
      }
    } else if (data && typeof data === 'object') {
      for (const field in changes) {
        if (field in data) {
          data[field] = changes[field];
          applied.push(field);
        }
      }
    }
    return applied;
  }

  function patchText(rawText) {
    try {
      const data = JSON.parse(rawText);
      const applied = applyPatch(data, CHANGES);
      const missing = Object.keys(CHANGES).filter((f) => !applied.includes(f));
      return JSON.stringify(data);
    } catch (e) {
      return rawText;
    }
  }

  const origOpen = XMLHttpRequest.prototype.open;
  const origSend = XMLHttpRequest.prototype.send;
  const responseTextDesc = Object.getOwnPropertyDescriptor(XMLHttpRequest.prototype, 'responseText');
  const responseDesc = Object.getOwnPropertyDescriptor(XMLHttpRequest.prototype, 'response');

  XMLHttpRequest.prototype.open = function (method, url, ...rest) {
    this._patchTarget = isTarget(url);
    if (this._patchTarget && !this._patchInstalled) {
      this._patchInstalled = true;
      let cachedRaw = null;
      let cachedPatched = null;
      const getPatchedText = () => {
        const raw = responseTextDesc.get.call(this);
        if (raw !== cachedRaw) {
          cachedRaw = raw;
          cachedPatched = patchText(raw);
        }
        return cachedPatched;
      };
      Object.defineProperty(this, 'responseText', { get: getPatchedText, configurable: true });
      Object.defineProperty(this, 'response', {
        get: () => {
          if (this.responseType === '' || this.responseType === 'text') return getPatchedText();
          return responseDesc.get.call(this);
        },
        configurable: true,
      });
    }
    return origOpen.call(this, method, url, ...rest);
  };

  XMLHttpRequest.prototype.send = function (...args) {
    return origSend.apply(this, args);
  };

  const origFetch = window.fetch;
  window.fetch = async function (...args) {
    const response = await origFetch.apply(this, args);
    const url = args[0] instanceof Request ? args[0].url : args[0];
    if (!isTarget(url)) return response;
    const text = await response.clone().text();
    const newText = patchText(text);
    const headers = new Headers(response.headers);
    headers.delete('content-length');
    return new Response(newText, { status: response.status, statusText: response.statusText, headers });
  };
})();
