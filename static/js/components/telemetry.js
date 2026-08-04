import { store } from '../state.js';

export class TelemetryComponent {
  constructor() {
    this.headerStats = document.getElementById('headerStats');
    this.statPage = document.getElementById('statPage');
    this.statTotal = document.getElementById('statTotal');
    this.statTime = document.getElementById('statTime');

    this.progressBar = document.getElementById('progressBar');
    this.progressText = document.getElementById('progressText');

    this.telemetry = document.getElementById('telemetry');
    this.telPages = document.getElementById('telPages');
    this.telOcr = document.getElementById('telOcr');
    this.telAvg = document.getElementById('telAvg');
    this.telTotal = document.getElementById('telTotal');

    this.downloadBar = document.getElementById('downloadBar');
    this.downloadBtn = document.getElementById('downloadBtn');
    this.fmtMd = document.getElementById('fmtMd');
    this.fmtEpub = document.getElementById('fmtEpub');

    this.currentFormat = 'md';

    this.initEvents();
  }

  initEvents() {
    store.addEventListener('change:jobId', () => {
      this.headerStats.style.display = 'flex';
      this.telemetry.style.display = 'block';
    });

    store.addEventListener('change:totalPages', e => {
      this.statTotal.textContent = e.detail;
      this.telPages.textContent = `0 / ${e.detail}`;
    });

    store.addEventListener('change:progressMsg', e => {
      this.progressText.textContent = e.detail;
    });

    store.addEventListener('change:latestPageDone', e => {
      const d = e.detail;
      const pct = (d.pageno / d.total) * 100;
      this.progressBar.style.width = pct + '%';
      this.progressText.textContent = `Page ${d.pageno} of ${d.total} — ${d.time_sec}s`;

      this.statPage.textContent = d.pageno;
      this.statTime.textContent = Math.round(d.cumulative_sec) + 's';

      this.telPages.textContent = `${d.pageno} / ${d.total}`;
      this.telOcr.textContent = d.cumulative_sec.toFixed(0) + 's';
      this.telAvg.textContent = (d.cumulative_sec / d.pageno).toFixed(1) + 's';

      // Show download bar as soon as first page completes (allowing partial downloads)
      if (this.downloadBar) {
        this.downloadBar.style.display = 'flex';
      }

      if (store.get('currentPage') === d.pageno - 1 && d.pageno < d.total) {
        store.set('currentPage', d.pageno);
      }
    });

    store.addEventListener('change:isCompleted', () => {
      this.progressBar.style.width = '100%';
      this.progressText.textContent = '✅ Complete!';
      if (this.downloadBar) {
        this.downloadBar.style.display = 'flex';
      }

      const startTime = store.get('startTime');
      if (startTime) {
        this.statTime.textContent = Math.round((Date.now() - startTime) / 1000) + 's';
      }

      const comp = store.get('completionData');
      if (comp && comp.telemetry) {
        this.telTotal.textContent = (comp.telemetry.total_sec || 0).toFixed(0) + 's';
      }
    });

    // Format toggles
    if (this.fmtMd && this.fmtEpub) {
      this.fmtMd.addEventListener('click', () => this.setFormat('md'));
      this.fmtEpub.addEventListener('click', () => this.setFormat('epub'));
    }

    if (this.downloadBtn) {
      this.downloadBtn.addEventListener('click', () => {
        const jobId = store.get('jobId');
        if (jobId) {
          window.open(`/download/${jobId}?format=${this.currentFormat}`, '_blank');
        }
      });
    }
  }

  setFormat(fmt) {
    this.currentFormat = fmt;
    if (fmt === 'md') {
      this.fmtMd.classList.add('active');
      this.fmtEpub.classList.remove('active');
      this.downloadBtn.textContent = '⬇ Download Markdown (.md)';
    } else {
      this.fmtEpub.classList.add('active');
      this.fmtMd.classList.remove('active');
      this.downloadBtn.textContent = '⬇ Download EPUB (.epub)';
    }
  }
}
