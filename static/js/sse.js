import { store } from './state.js';

export class SSEManager {
  constructor() {
    this.evtSource = null;
    this.reconnectTimer = null;
  }

  listen(jobId) {
    if (this.evtSource) this.close();
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);

    this.evtSource = new EventSource(`/api/stream/${jobId}`);

    this.evtSource.addEventListener('progress', e => {
      try {
        const d = JSON.parse(e.data);
        store.set('progressMsg', d.msg);
      } catch (ex) {
        console.warn('progress event parse error:', ex);
      }
    });

    this.evtSource.addEventListener('page_done', e => {
      try {
        const d = JSON.parse(e.data);
        store.updatePageData(d.pageno, d.text);
        store.set('latestPageDone', d);
      } catch (ex) {
        console.warn('page_done parse error:', ex);
      }
    });

    this.evtSource.addEventListener('done', e => {
      try {
        const d = JSON.parse(e.data);
        store.set('isProcessing', false);
        store.set('isCompleted', true);
        store.set('completionData', d);
      } catch (ex) {
        console.warn('done parse error:', ex);
      }
      this.close();
    });

    this.evtSource.addEventListener('error', e => {
      let isFinalError = false;
      try {
        const d = JSON.parse(e.data);
        store.set('progressMsg', '⚠️ ' + (d.msg || 'Processing issue'));
        isFinalError = true;
      } catch (ex) {
        store.set('progressMsg', '🔄 Connection drop — reconnecting stream...');
      }

      this.close();

      if (!isFinalError && store.get('isProcessing') && !store.get('isCompleted')) {
        this.reconnectTimer = setTimeout(() => {
          if (store.get('isProcessing') && !store.get('isCompleted')) {
            this.listen(jobId);
          }
        }, 2000);
      }
    });

    this.evtSource.onerror = () => {
      if (store.get('isCompleted')) {
        this.close();
      }
    };
  }

  close() {
    if (this.evtSource) {
      this.evtSource.close();
      this.evtSource = null;
    }
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }
}

export const sseManager = new SSEManager();
