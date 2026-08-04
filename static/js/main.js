import { store } from './state.js';
import { ApiClient } from './api.js';
import { sseManager } from './sse.js';
import { ThemeManager } from './utils/theme.js';
import { DrawerComponent } from './components/drawer.js';
import { DropzoneComponent } from './components/dropzone.js';
import { PdfViewerComponent } from './components/pdf-viewer.js';
import { ReaderComponent } from './components/reader.js';
import { TelemetryComponent } from './components/telemetry.js';

document.addEventListener('DOMContentLoaded', async () => {
  new ThemeManager();
  new DrawerComponent();
  new DropzoneComponent();
  new PdfViewerComponent();
  new ReaderComponent();
  new TelemetryComponent();

  // Check URL hash for job ID switching (e.g. #job_id)
  const hashJobId = window.location.hash ? window.location.hash.substring(1) : null;
  const savedJobId = hashJobId || store.get('jobId');

  if (savedJobId) {
    try {
      const sess = await ApiClient.getSession(savedJobId);
      if (sess && !sess.error) {
        console.log('Restoring session:', savedJobId, sess);

        const dz = document.getElementById('dropzone');
        const ws = document.getElementById('workspace');
        dz.classList.add('hidden');
        ws.classList.add('active');

        store.set('jobId', savedJobId);
        store.set('totalPages', sess.pages_total || 0);
        store.set('currentPage', 0);

        if (sess.completed_pages) {
          store.restorePages(sess.completed_pages);
        }

        const missing = sess.missing_pages || [];
        if (sess.status === 'done' && missing.length === 0) {
          store.set('isCompleted', true);
          store.set('progressMsg', '✅ Completed');
        } else if (sess.status === 'paused') {
          store.set('progressMsg', '⏸️ Job Paused');
        } else {
          store.set('isProcessing', true);
          store.set('progressMsg', 'Connected to conversion stream...');
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
