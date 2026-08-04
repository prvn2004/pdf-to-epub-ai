import { store } from '../state.js';

export class DrawerComponent {
  constructor() {
    this.drawerToggleBtn = document.getElementById('drawerToggleBtn');
    this.jobDrawer = document.getElementById('jobDrawer');
    this.jobList = document.getElementById('jobList');
    this.jobCountBadge = document.getElementById('jobCountBadge');
    
    this.pollTimer = null;
    this.init();
  }

  init() {
    if (this.drawerToggleBtn && this.jobDrawer) {
      this.drawerToggleBtn.addEventListener('click', () => {
        this.jobDrawer.classList.toggle('open');
        this.fetchJobsList();
      });
    }

    store.addEventListener('change:jobId', () => {
      this.fetchJobsList();
      this.startPolling();
    });

    store.addEventListener('change:isCompleted', () => {
      this.fetchJobsList();
      this.stopPolling();
    });

    this.fetchJobsList();
  }

  startPolling() {
    this.stopPolling();
    this.pollTimer = setInterval(() => this.fetchJobsList(), 5000);
  }

  stopPolling() {
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
  }

  async fetchJobsList() {
    try {
      const resp = await fetch('/api/jobs');
      if (resp.ok) {
        const data = await resp.json();
        if (data.jobs) {
          this.renderJobs(data.jobs);
          // Check if any job is still actively processing
          const hasActiveJobs = data.jobs.some(j => j.status === 'processing');
          if (!hasActiveJobs) {
            this.stopPolling();
          }
        }
      }
    } catch (e) {
      console.warn('[Drawer] Failed to fetch jobs:', e);
    }
  }

  renderJobs(jobs) {
    if (!this.jobList) return;

    if (this.jobCountBadge) {
      this.jobCountBadge.textContent = jobs.length;
      this.jobCountBadge.style.display = jobs.length > 0 ? 'inline-block' : 'none';
    }

    const currentJobId = store.get('jobId');
    this.jobList.innerHTML = '';

    if (jobs.length === 0) {
      this.jobList.innerHTML = '<div class="drawer-empty">No active conversion jobs</div>';
      return;
    }

    jobs.forEach(job => {
      const isSelected = job.job_id === currentJobId;
      const card = document.createElement('div');
      card.className = `job-card ${isSelected ? 'selected' : ''}`;
      
      let badgeClass = 'bg-blue';
      let statusText = job.status;
      if (job.status === 'done') { badgeClass = 'bg-green'; statusText = 'Done ✅'; }
      else if (job.status === 'paused') { badgeClass = 'bg-amber'; statusText = 'Paused ⏸️'; }
      else if (job.status === 'processing') { badgeClass = 'bg-blue'; statusText = `Converting (${job.pages_done}/${job.pages_total})`; }
      else if (job.status === 'error' || job.status === 'incomplete') { badgeClass = 'bg-red'; statusText = 'Incomplete ⚠️'; }

      card.innerHTML = `
        <div class="job-card-header">
          <div class="job-title" title="${job.title}">${job.title}</div>
          <span class="status-badge ${badgeClass}">${statusText}</span>
        </div>
        <div class="job-card-actions">
          ${job.status === 'processing' ? `<button class="btn-icon pause-btn" title="Pause">⏸️</button>` : ''}
          ${job.status === 'paused' || job.status === 'incomplete' ? `<button class="btn-icon resume-btn" title="Resume">▶️</button>` : ''}
          <button class="btn-icon delete-btn" title="Delete">🗑️</button>
        </div>
      `;

      card.addEventListener('click', (e) => {
        if (!e.target.classList.contains('btn-icon')) {
          this.switchJob(job.job_id);
        }
      });

      const pauseBtn = card.querySelector('.pause-btn');
      if (pauseBtn) {
        pauseBtn.addEventListener('click', async (e) => {
          e.stopPropagation();
          await fetch(`/api/pause/${job.job_id}`, { method: 'POST' });
          this.fetchJobsList();
        });
      }

      const resumeBtn = card.querySelector('.resume-btn');
      if (resumeBtn) {
        resumeBtn.addEventListener('click', async (e) => {
          e.stopPropagation();
          await fetch(`/api/resume/${job.job_id}`, { method: 'POST' });
          this.startPolling();
          this.fetchJobsList();
        });
      }

      const deleteBtn = card.querySelector('.delete-btn');
      if (deleteBtn) {
        deleteBtn.addEventListener('click', async (e) => {
          e.stopPropagation();
          if (confirm(`Delete document "${job.title}"?`)) {
            await fetch(`/api/job/${job.job_id}`, { method: 'DELETE' });
            if (job.job_id === currentJobId) {
              window.location.reload();
            } else {
              this.fetchJobsList();
            }
          }
        });
      }

      this.jobList.appendChild(card);
    });
  }

  switchJob(jobId) {
    if (jobId === store.get('jobId')) return;
    store.set('jobId', jobId);
    store.set('currentPage', 0);
    store.set('pages', {});
    window.location.hash = jobId;
    window.location.reload();
  }
}
