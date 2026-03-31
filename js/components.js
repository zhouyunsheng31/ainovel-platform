/**
 * AI小说拆书系统 - UI组件模块
 * 可复用的前端组件
 */

// ================================
// 文件上传组件
// ================================

class FileUploader {
  constructor(container, options = {}) {
    this.container = typeof container === 'string' 
      ? document.querySelector(container) 
      : container;
    
    if (!this.container) {
      throw new Error('FileUploader: Container not found');
    }
    
    const acceptedFormats = (options.acceptedFormats || ['.txt', '.epub', '.doc', '.docx', '.pdf'])
      .map(format => format.startsWith('.') ? format.toLowerCase() : `.${format.toLowerCase()}`);
    
    this.options = {
      acceptedFormats,
      maxFileSize: options.maxFileSize || 50 * 1024 * 1024, // 50MB
      onUpload: options.onUpload || null,
      onProgress: options.onProgress || null,
      onError: options.onError || null
    };
    
    this.file = null;
    this.init();
  }
  
  init() {
    this.container.innerHTML = `
      <div class="upload-zone" id="uploadZone">
        <div class="upload-icon">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5a4.5 4.5 0 01-1.41-8.775 5.25 5.25 0 0110.233-2.33 3 3 0 013.758 3.848A3.752 3.752 0 0118 19.5H6.75z" />
          </svg>
        </div>
        <p class="upload-text">拖拽文件到此处，或点击选择文件</p>
        <p class="upload-hint">支持上传小说文件进行拆解分析</p>
        <div class="upload-formats">
          ${this.options.acceptedFormats.map(f => 
            `<span class="format-badge">${f}</span>`
          ).join('')}
        </div>
        <input type="file" class="file-input" id="fileInput" 
               accept="${this.options.acceptedFormats.join(',')}">
      </div>
      <div class="upload-progress hidden" id="uploadProgress">
        <div class="progress-bar">
          <div class="progress-fill" id="progressFill"></div>
        </div>
        <div class="progress-text">
          <span id="progressLabel">上传中...</span>
          <span id="progressPercent">0%</span>
        </div>
      </div>
      <div class="upload-error error-list hidden" id="uploadErrors"></div>
    `;
    
    this.zone = this.container.querySelector('#uploadZone');
    this.fileInput = this.container.querySelector('#fileInput');
    this.progressContainer = this.container.querySelector('#uploadProgress');
    this.progressFill = this.container.querySelector('#progressFill');
    this.progressLabel = this.container.querySelector('#progressLabel');
    this.progressPercent = this.container.querySelector('#progressPercent');
    this.errorContainer = this.container.querySelector('#uploadErrors');
    
    this.bindEvents();
  }
  
  bindEvents() {
    // 点击上传
    this.zone.addEventListener('click', () => {
      this.fileInput.click();
    });
    
    // 文件选择
    this.fileInput.addEventListener('change', (e) => {
      if (e.target.files.length > 0) {
        this.handleFile(e.target.files[0]);
      }
    });
    
    // 拖拽事件
    this.zone.addEventListener('dragover', (e) => {
      e.preventDefault();
      this.zone.classList.add('drag-over');
    });
    
    this.zone.addEventListener('dragleave', (e) => {
      e.preventDefault();
      this.zone.classList.remove('drag-over');
    });
    
    this.zone.addEventListener('drop', (e) => {
      e.preventDefault();
      this.zone.classList.remove('drag-over');
      if (e.dataTransfer.files.length > 0) {
        this.handleFile(e.dataTransfer.files[0]);
      }
    });
  }
  
  handleFile(file) {
    // 清除之前的错误
    this.errorContainer.innerHTML = '';
    this.errorContainer.classList.add('hidden');
    
    // 验证文件格式
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!this.options.acceptedFormats.includes(ext)) {
      this.showError('文件格式不支持', `仅支持: ${this.options.acceptedFormats.join(', ')}`);
      return;
    }
    
    // 验证文件大小
    if (file.size > this.options.maxFileSize) {
      const maxSizeMB = (this.options.maxFileSize / 1024 / 1024).toFixed(0);
      this.showError('文件过大', `文件大小不能超过 ${maxSizeMB}MB`);
      return;
    }
    
    this.file = file;
    this.zone.classList.add('hidden');
    this.progressContainer.classList.remove('hidden');
    this.simulateProgress();
    
    // 调用上传回调
    if (this.options.onUpload) {
      this.options.onUpload(file);
    }
  }
  
  showError(title, message) {
    this.errorContainer.innerHTML = `
      <div class="error-item">
        <svg class="error-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" width="24" height="24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <div class="error-content">
          <div class="error-title">${title}</div>
          <div class="error-message">${message}</div>
        </div>
      </div>
    `;
    this.errorContainer.classList.remove('hidden');
    
    if (this.options.onError) {
      this.options.onError(title, message);
    }
  }
  
  simulateProgress() {
    let progress = 0;
    const interval = setInterval(() => {
      progress += Math.random() * 10;
      if (progress > 100) progress = 100;
      this.updateProgress(progress);
      
      if (progress >= 100 && this.options.onProgress) {
        clearInterval(interval);
        this.progressLabel.textContent = '上传完成';
        this.options.onProgress(100);
      }
    }, 100);
  }
  
  updateProgress(percent) {
    this.progressFill.style.width = `${percent}%`;
    this.progressPercent.textContent = `${Math.round(percent)}%`;
  }
  
  reset() {
    this.file = null;
    this.zone.classList.remove('hidden');
    this.progressContainer.classList.add('hidden');
    this.progressFill.style.width = '0%';
    this.progressPercent.textContent = '0%';
    this.progressLabel.textContent = '上传中...';
    this.errorContainer.innerHTML = '';
    this.errorContainer.classList.add('hidden');
    this.fileInput.value = '';
  }
}

// ================================
// 进度监控组件
// ================================

class ProgressMonitor {
  constructor(container, options = {}) {
    this.container = typeof container === 'string'
      ? document.querySelector(container)
      : container;
    
    if (!this.container) {
      throw new Error('ProgressMonitor: Container not found');
    }
    
    this.stages = options.stages || [
      { id: 'fileUpload', name: '文件上传', icon: 'upload' },
      { id: 'textPreprocess', name: '文本预处理', icon: 'preprocess' },
      { id: 'chapterOutline', name: '章纲提取', icon: 'chapter' },
      { id: 'coarseOutline', name: '粗纲生成', icon: 'coarse' },
      { id: 'mainOutline', name: '大纲生成', icon: 'main' },
      { id: 'worldOutline', name: '世界纲生成', icon: 'world' }
    ];
    
    this.state = {};
    this.init();
  }
  
  init() {
    this.stages.forEach(stage => {
      this.state[stage.id] = {
        status: 'pending',
        progress: 0,
        total: 0,
        completed: 0,
        error: null
      };
    });
    
    this.render();
  }
  
  render() {
    this.container.innerHTML = `
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">处理进度</h3>
        </div>
        <div class="card-body">
          <div class="processing-status">
            ${this.stages.map(stage => this.renderStage(stage)).join('')}
          </div>
        </div>
      </div>
      <div class="card" id="errorCard" style="display: none;">
        <div class="card-header">
          <h3 class="card-title">错误信息</h3>
        </div>
        <div class="card-body">
          <div class="error-list" id="errorList"></div>
        </div>
      </div>
    `;
    
    this.errorCard = this.container.querySelector('#errorCard');
    this.errorList = this.container.querySelector('#errorList');
  }
  
  renderStage(stage) {
    const state = this.state[stage.id];
    const iconSvg = this.getIconSvg(stage.icon);
    
    return `
      <div class="status-item" data-stage="${stage.id}">
        <div class="status-icon ${state.status}">
          ${iconSvg}
        </div>
        <div class="status-content">
          <div class="status-title">${stage.name}</div>
          <div class="status-progress">
            ${this.renderProgress(stage.id, state)}
          </div>
          ${state.error ? `<div class="status-detail" style="color: var(--error);">${state.error}</div>` : ''}
        </div>
      </div>
    `;
  }
  
  getIconSvg(type) {
    const icons = {
      upload: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5" width="20" height="20"><path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" /></svg>',
      preprocess: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5" width="20" height="20"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" /></svg>',
      chapter: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5" width="20" height="20"><path stroke-linecap="round" stroke-linejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" /></svg>',
      coarse: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5" width="20" height="20"><path stroke-linecap="round" stroke-linejoin="round" d="M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 010 3.75H5.625a1.875 1.875 0 010-3.75z" /></svg>',
      main: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5" width="20" height="20"><path stroke-linecap="round" stroke-linejoin="round" d="M9 4.5v15m6-15v15m-10.875 0h15.75c.621 0 1.125-.504 1.125-1.125V5.625c0-.621-.504-1.125-1.125-1.125H4.125C3.504 4.5 3 5.004 3 5.625v12.75c0 .621.504 1.125 1.125 1.125z" /></svg>',
      world: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5" width="20" height="20"><path stroke-linecap="round" stroke-linejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m-.686-5.671a9.165 9.165 0 01-.492 2.668m-15.686 0A8.959 8.959 0 013 12c0-.778.099-1.533.284-2.253m.686 5.671a9.017 9.017 0 003.944 4.725m7.686-16.35a9.004 9.004 0 011.952 2.392" /></svg>'
    };
    return icons[type] || icons.upload;
  }
  
  renderProgress(stageId, state) {
    if (state.status === 'pending') {
      return '等待中';
    }
    
    if (state.status === 'completed') {
      return '完成';
    }
    
    if (state.status === 'error') {
      return '失败';
    }
    
    if (state.total > 0) {
      return `${state.completed}/${state.total} (${Math.round(state.progress)}%)`;
    }
    
    return `${Math.round(state.progress)}%`;
  }
  
  updateStage(stageId, data) {
    if (this.state[stageId]) {
      Object.assign(this.state[stageId], data);
      this.updateStageElement(stageId);
    }
  }

  update(status = {}) {
    this.stages.forEach(stage => {
      const nextState = status[stage.id];
      if (nextState) {
        this.updateStage(stage.id, nextState);
      }
    });
  }
  
  updateStageElement(stageId) {
    const stage = this.stages.find(s => s.id === stageId);
    if (!stage) return;
    
    const element = this.container.querySelector(`[data-stage="${stageId}"]`);
    if (!element) return;
    
    const state = this.state[stageId];
    const icon = element.querySelector('.status-icon');
    icon.className = `status-icon ${state.status}`;
    
    const progressEl = element.querySelector('.status-progress');
    progressEl.textContent = this.renderProgress(stageId, state);
  }
  
  addError(stageId, error) {
    this.updateStage(stageId, { status: 'error', error: error.message });
    
    this.errorCard.style.display = 'block';
    
    const stage = this.stages.find(s => s.id === stageId);
    const errorItem = document.createElement('div');
    errorItem.className = 'error-item';
    errorItem.innerHTML = `
      <svg class="error-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" width="24" height="24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <div class="error-content">
        <div class="error-title">${stage ? stage.name : stageId}</div>
        <div class="error-message">${error.message}</div>
      </div>
    `;
    this.errorList.appendChild(errorItem);
  }
  
  reset() {
    this.stages.forEach(stage => {
      this.state[stage.id] = {
        status: 'pending',
        progress: 0,
        total: 0,
        completed: 0,
        error: null
      };
    });
    this.errorList.innerHTML = '';
    this.errorCard.style.display = 'none';
    this.render();
  }
}

// ================================
// Toast消息组件
// ================================

class ToastManager {
  constructor() {
    this.container = null;
    this.init();
  }
  
  init() {
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      container.className = 'toast-container';
      document.body.appendChild(container);
    }
    this.container = container;
  }
  
  show(message, type = 'info', duration = 3000) {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    this.container.appendChild(toast);
    
    setTimeout(() => {
      toast.style.animation = 'slideOut 0.3s ease forwards';
      setTimeout(() => toast.remove(), 300);
    }, duration);
    
    return toast;
  }
  
  success(message) { return this.show(message, 'success'); }
  error(message) { return this.show(message, 'error'); }
  warning(message) { return this.show(message, 'warning'); }
  info(message) { return this.show(message, 'info'); }
}

// 创建全局Toast实例
const toast = new ToastManager();

// 导出组件
export { FileUploader, ProgressMonitor, ToastManager, toast };