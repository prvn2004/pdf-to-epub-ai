import { store } from './state.js';
import { ApiClient } from './api.js';
import { sseManager } from './sse.js';
import { DropzoneComponent } from './components/dropzone.js';
import { PdfViewerComponent } from './components/pdf-viewer.js';
import { ReaderComponent } from './components/reader.js';
import { TelemetryComponent } from './components/telemetry.js';

document.addEventListener('DOMContentLoaded', async () => {
  new DropzoneComponent();
  new PdfViewerComponent();
  new ReaderComponent();
  new TelemetryComponent();

  // Check for active/resumable job in localStorage
  const savedJobId = store.get('jobId');
  if (savedJobId) {
    try {
      const sess = await ApiClient.getSession(savedJobId);
      if (sess && !sess.error) {
        console.log('Restoring saved session:', savedJobId, sess);

        const dz = document.getElementById('dropzone');
        const ws = document.getElementById('workspace');
        dz.classList.add('hidden');
        ws.classList.add('active');

        store.set('totalPages', sess.pages_total || 0);
        store.set('currentPage', 0);

        if (sess.completed_pages) {
          store.restorePages(sess.completed_pages);
        }

        const missing = sess.missing_pages || [];
        if (sess.status === 'done' && missing.length === 0) {
          store.set('isCompleted', true);
          store.set('progressMsg', '✅ Completed (Restored from Session)');
        } else {
          store.set('isProcessing', true);
          store.set('progressMsg', missing.length > 0
            ? `Resuming processing for ${missing.length} uncompleted page(s)...`
            : 'Resuming processing stream...'
          );
          await ApiClient.resumeJob(savedJobId);
          sseManager.listen(savedJobId);
        }
      } else {
        store.clearJob();
      }
    } catch (err) {
      console.warn('Could not restore session:', err);
      store.clearJob();
    }
  }
});
