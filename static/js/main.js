import { ThemeManager } from './utils/theme.js';
import { ApiClient } from './api.js';
import { sseManager } from './sse.js';
import { store } from './state.js';

document.addEventListener('DOMContentLoaded', async () => {
  new ThemeManager();

  // DOM Elements
  const uploadCard = document.getElementById('uploadCard');
  const fileInput = document.getElementById('fileInput');
  const metaTitle = document.getElementById('metaTitle');
  const metaAuthor = document.getElementById('metaAuthor');

  const progressCard = document.getElementById('progressCard');
  const docTitle = document.getElementById('docTitle');
  const pctBadge = document.getElementById('pctBadge');
  const progressBar = document.getElementById('progressBar');
  const progressText = document.getElementById('progressText');
  const btnPause = document.getElementById('btnPause');
  const btnResume = document.getElementById('btnResume');
  const btnCancel = document.getElementById('btnCancel');

  const telPages = document.getElementById('telPages');
  const telAvg = document.getElementById('telAvg');
  const telTime = document.getElementById('telTime');

  const downloadCard = document.getElementById('downloadCard');
  const fmtMd = document.getElementById('fmtMd');
  const fmtEpub = document.getElementById('fmtEpub');
  const downloadBtn = document.getElementById('downloadBtn');

  let currentFormat = 'md';
  let processedPagesCount = 0;

  // 1. Check URL query parameter for ?job=SECRET_TOKEN
  const urlParams = new URLSearchParams(window.location.search);
  const urlJobId = urlParams.get('job') || store.get('jobId');

  if (urlJobId) {
    try {
      const sess = await ApiClient.getSession(urlJobId);
      if (sess && !sess.error) {
        attachToJob(urlJobId, sess);
      } else {
        resetToUpload();
      }
    } catch (e) {
      console.warn('Job recovery failed:', e);
      resetToUpload();
    }
  }

  // 2. Dropzone events
  uploadCard.addEventListener('click', e => {
    if (e.target.tagName !== 'INPUT') fileInput.click();
  });
  uploadCard.addEventListener('dragover', e => { e.preventDefault(); uploadCard.classList.add('drag'); });
  uploadCard.addEventListener('dragleave', () => uploadCard.classList.remove('drag'));
  uploadCard.addEventListener('drop', e => {
    e.preventDefault();
    uploadCard.classList.remove('drag');
    if (e.dataTransfer.files.length) handleFileUpload(e.dataTransfer.files[0]);
  });
  fileInput.addEventListener('change', () => {
    if (fileInput.files.length) handleFileUpload(fileInput.files[0]);
  });

  // 3. Upload File Handler
  async function handleFileUpload(file) {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      return alert('Please select a valid PDF file.');
    }

    const title = metaTitle.value || file.name.replace(/\.pdf$/i, '');
    const author = metaAuthor.value || 'Unknown';

    uploadCard.style.display = 'none';
    progressCard.style.display = 'flex';
    docTitle.textContent = title;
    progressText.textContent = 'Uploading document...';
    progressBar.style.width = '0%';
    pctBadge.textContent = '0%';
    processedPagesCount = 0;
    store.set('startTime', Date.now());

    try {
      const data = await ApiClient.uploadPdf(file, title, author);
      const jobId = data.job_id;
      
      // Update URL query parameter
      window.history.pushState({}, '', `/?job=${jobId}`);
      store.set('jobId', jobId);

      connectToStream(jobId);
    } catch (err) {
      alert(`Upload failed: ${err.message}`);
      resetToUpload();
    }
  }

  function attachToJob(jobId, sess) {
    store.set('jobId', jobId);
    window.history.pushState({}, '', `/?job=${jobId}`);

    uploadCard.style.display = 'none';
    progressCard.style.display = 'flex';
    docTitle.textContent = sess.title || 'Book';

    const total = sess.pages_total || 0;
    processedPagesCount = sess.pages_done || 0;
    const pct = total > 0 ? Math.round((processedPagesCount / total) * 100) : 0;

    progressBar.style.width = `${pct}%`;
    pctBadge.textContent = `${pct}%`;
    telPages.textContent = `${processedPagesCount} / ${total}`;

    if (processedPagesCount > 0) {
      downloadCard.style.display = 'flex';
    }

    if (sess.status === 'done') {
      progressText.textContent = '✅ Conversion Complete!';
      btnPause.style.display = 'none';
      btnResume.style.display = 'none';
      downloadCard.style.display = 'flex';
    } else if (sess.status === 'paused') {
      progressText.textContent = '⏸️ Processing Paused';
      btnPause.style.display = 'none';
      btnResume.style.display = 'inline-block';
    } else {
      btnPause.style.display = 'inline-block';
      btnResume.style.display = 'none';
      connectToStream(jobId);
    }
  }

  function connectToStream(jobId) {
    sseManager.listen(jobId);

    store.addEventListener('change:progressMsg', e => {
      progressText.textContent = e.detail;
    });

    store.addEventListener('change:latestPageDone', e => {
      const d = e.detail;
      processedPagesCount += 1;
      const count = Math.min(processedPagesCount, d.total);
      const pct = Math.round((count / d.total) * 100);
      
      progressBar.style.width = `${pct}%`;
      pctBadge.textContent = `${pct}%`;

      progressText.textContent = `${count} of ${d.total} pages processed (${pct}%) — ⚡ Download available anytime!`;
      telPages.textContent = `${count} / ${d.total}`;
      telAvg.textContent = count > 0 ? `${(d.cumulative_sec / count).toFixed(1)}s` : '—';
      telTime.textContent = `${Math.round(d.cumulative_sec)}s`;

      downloadCard.style.display = 'flex';
      btnPause.style.display = 'inline-block';
      btnResume.style.display = 'none';
    });

    store.addEventListener('change:isCompleted', () => {
      progressBar.style.width = '100%';
      pctBadge.textContent = '100%';
      progressText.textContent = '✅ Conversion Complete! Download files below.';
      btnPause.style.display = 'none';
      btnResume.style.display = 'none';
      downloadCard.style.display = 'flex';

      const startTime = store.get('startTime');
      if (startTime) {
        telTime.textContent = `${Math.round((Date.now() - startTime) / 1000)}s`;
      }
    });
  }

  function resetToUpload() {
    store.clearJob();
    sseManager.close();
    window.history.pushState({}, '', '/');
    
    uploadCard.style.display = 'flex';
    progressCard.style.display = 'none';
    downloadCard.style.display = 'none';
    fileInput.value = '';
    processedPagesCount = 0;
  }

  // Control Buttons
  btnPause.addEventListener('click', async () => {
    const jobId = store.get('jobId');
    if (jobId) {
      await fetch(`/api/pause/${jobId}`, { method: 'POST' });
      btnPause.style.display = 'none';
      btnResume.style.display = 'inline-block';
      progressText.textContent = '⏸️ Conversion Paused';
    }
  });

  btnResume.addEventListener('click', async () => {
    const jobId = store.get('jobId');
    if (jobId) {
      await fetch(`/api/resume/${jobId}`, { method: 'POST' });
      btnResume.style.display = 'none';
      btnPause.style.display = 'inline-block';
      connectToStream(jobId);
    }
  });

  btnCancel.addEventListener('click', () => {
    if (confirm('Start new conversion? Your current file can still be accessed via its URL link.')) {
      resetToUpload();
    }
  });

  // Format Toggles & Download Button
  fmtMd.addEventListener('click', () => setFormat('md'));
  fmtEpub.addEventListener('click', () => setFormat('epub'));

  function setFormat(fmt) {
    currentFormat = fmt;
    if (fmt === 'md') {
      fmtMd.classList.add('active');
      fmtEpub.classList.remove('active');
      downloadBtn.textContent = '⬇ Download Markdown (.md)';
    } else {
      fmtEpub.classList.add('active');
      fmtMd.classList.remove('active');
      downloadBtn.textContent = '⬇ Download EPUB (.epub)';
    }
  }

  downloadBtn.addEventListener('click', () => {
    const jobId = store.get('jobId');
    if (jobId) {
      window.open(`/download/${jobId}?format=${currentFormat}`, '_blank');
    }
  });
});
