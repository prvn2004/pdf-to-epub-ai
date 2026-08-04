import { store } from './state.js';

export class SSEManager {
  constructor() {
    this.evtSource = null;
  }

  listen(jobId) {
    if (this.evtSource) this.close();

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
      try {
        const d = JSON.parse(e.data);
        store.set('progressMsg', '❌ ' + (d.msg || 'Unknown error'));
      } catch (ex) {
        store.set('progressMsg', '❌ Connection issue — retrying...');
      }
      this.close();
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
  }
}

export const sseManager = new SSEManager();
