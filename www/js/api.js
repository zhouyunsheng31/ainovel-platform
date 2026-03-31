/**
 * AI小说拆书系统 - API模块
 * 处理所有HTTP请求和WebSocket通信
 * 支持Mock模式和真实API模式切换
 */

class APIClient {
  constructor(config = {}) {
    // 基础配置
    this.baseUrl = config.baseUrl || '/api/v1';
    this.wsUrl = config.wsUrl || this._deriveWsUrl(this.baseUrl);
    
    // Mock模式（开发阶段）
    this.mockMode = config.mockMode !== false;
    
    // WebSocket实例
    this.ws = null;
    this.wsReconnectAttempts = 0;
    this.wsMaxReconnectAttempts = 5;
    this.wsReconnectDelay = 1000;
    
    // 请求超时
    this.timeout = config.timeout || 60000;
    
    // 事件监听器
    this.listeners = new Map();
  }
  
  _deriveWsUrl(baseUrl) {
    try {
      const url = new URL(baseUrl, window.location.origin);
      const wsProtocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
      return `${wsProtocol}//${url.host}/api/v1/ws`;
    } catch {
      return `ws://${window.location.host}/api/v1/ws`;
    }
  }
  
  // ================================
  // HTTP请求方法
  // ================================
  
  /**
   * 通用请求方法
   */
  async request(method, endpoint, data = null, options = {}) {
    if (this.mockMode) {
      return this.mockRequest(method, endpoint, data);
    }
    
    const url = `${this.baseUrl}${endpoint}`;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), options.timeout || this.timeout);
    
    try {
      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers
        },
        body: data ? JSON.stringify(data) : null,
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: { message: response.statusText } }));
        const errorMessage = errorData.detail?.message || errorData.message || `HTTP ${response.status}`;
        throw new Error(errorMessage);
      }
      
      return await response.json();
    } catch (error) {
      clearTimeout(timeoutId);
      if (error.name === 'AbortError') {
        throw new Error('请求超时');
      }
      throw error;
    }
  }
  
  /**
   * GET请求
   */
  async get(endpoint, options = {}) {
    return this.request('GET', endpoint, null, options);
  }
  
  /**
   * POST请求
   */
  async post(endpoint, data, options = {}) {
    return this.request('POST', endpoint, data, options);
  }
  
  /**
   * PUT请求
   */
  async put(endpoint, data, options = {}) {
    return this.request('PUT', endpoint, data, options);
  }
  
  /**
   * DELETE请求
   */
  async delete(endpoint, options = {}) {
    return this.request('DELETE', endpoint, null, options);
  }
  
  // ================================
  // 文件上传
  // ================================
  
  /**
   * 上传文件
   */
  async uploadFile(file, options = {}) {
    if (this.mockMode) {
      return this.mockFileUpload(file, options);
    }
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', options.title || file.name);
    if (options.author) {
      formData.append('author', options.author);
    }
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), options.timeout || this.timeout);
    
    try {
      const response = await fetch(`${this.baseUrl}/books/upload`, {
        method: 'POST',
        headers: options.headers || {},
        body: formData,
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: { message: response.statusText } }));
        const errorMessage = errorData.detail?.message || errorData.message || `上传失败: ${response.status}`;
        throw new Error(errorMessage);
      }
      
      return await response.json();
    } catch (error) {
      clearTimeout(timeoutId);
      if (error.name === 'AbortError') {
        throw new Error('上传超时');
      }
      throw error;
    }
  }
  
  // ================================
  // WebSocket通信
  // ================================
  
  /**
   * 连接WebSocket
   */
  connectWebSocket(taskId) {
    if (this.ws) {
      this.disconnectWebSocket();
    }
    
    if (this.mockMode) {
      this.setupMockWebSocket(taskId);
      return;
    }
    
    const url = `${this.wsUrl}/${taskId}`;
    
    try {
      this.ws = new WebSocket(url);
      
      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.wsReconnectAttempts = 0;
        this.emit('ws:connected');
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          this.ws.send(JSON.stringify({ type: 'get_status' }));
        }
      };
      
      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleWSMessage(data);
        } catch (e) {
          console.error('WebSocket message parse error:', e);
        }
      };
      
      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.emit('ws:error', error);
      };
      
      this.ws.onclose = () => {
        console.log('WebSocket closed');
        this.emit('ws:disconnected');
        this.attemptReconnect(taskId);
      };
    } catch (error) {
      console.error('WebSocket connection error:', error);
      this.emit('ws:error', error);
    }
  }
  
  /**
   * 断开WebSocket
   */
  disconnectWebSocket() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
  
  /**
   * WebSocket重连
   */
  attemptReconnect(taskId) {
    if (this.wsReconnectAttempts >= this.wsMaxReconnectAttempts) {
      console.log('Max reconnect attempts reached');
      return;
    }
    
    this.wsReconnectAttempts++;
    const delay = this.wsReconnectDelay * this.wsReconnectAttempts;
    
    setTimeout(() => {
      console.log(`Reconnecting... attempt ${this.wsReconnectAttempts}`);
      this.connectWebSocket(taskId);
    }, delay);
  }
  
  /**
   * 处理WebSocket消息
   */
  handleWSMessage(data) {
    const { type, payload } = data;
    
    switch (type) {
      case 'connected':
        this.emit('ws:connected', payload);
        break;
      case 'heartbeat':
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          this.ws.send(JSON.stringify({ type: 'ping' }));
        }
        break;
      case 'pong':
        break;
      case 'progress':
        this.emit('progress', payload);
        break;
      case 'error':
        this.emit('error', payload);
        break;
      case 'completed':
        this.emit('completed', payload);
        break;
      case 'outline_update':
        this.emit('outline_update', payload);
        break;
      case 'status_response':
        this.emit('status_response', payload);
        break;
      default:
        console.log('Unknown WS message type:', type);
    }
  }
  
  // ================================
  // 事件系统
  // ================================
  
  /**
   * 监听事件
   */
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);
  }
  
  /**
   * 移除事件监听
   */
  off(event, callback) {
    if (this.listeners.has(event)) {
      const callbacks = this.listeners.get(event);
      const index = callbacks.indexOf(callback);
      if (index > -1) {
        callbacks.splice(index, 1);
      }
    }
  }
  
  /**
   * 触发事件
   */
  emit(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach(callback => {
        try {
          callback(data);
        } catch (e) {
          console.error('Event listener error:', e);
        }
      });
    }
  }
  
  // ================================
  // Mock数据方法（开发阶段使用）
  // ================================
  
  /**
   * Mock请求处理
   */
  async mockRequest(method, endpoint, data) {
    // 模拟网络延迟
    await this.delay(300);
    
    // 根据endpoint返回mock数据
    if (endpoint === '/books') {
      return this.mockGetBooks();
    }
    
    if (endpoint.startsWith('/books/')) {
      const bookId = endpoint.split('/')[2];
      if (endpoint.endsWith('/tree')) {
        return this.mockGetOutlineTree(bookId);
      }
      return this.mockGetBook(bookId);
    }
    
    if (endpoint.startsWith('/outlines/')) {
      const outlineId = endpoint.split('/')[2];
      return this.mockGetOutline(outlineId);
    }
    
    throw new Error(`Unknown endpoint: ${endpoint}`);
  }
  
  /**
   * Mock文件上传
   */
  async mockFileUpload(file, options) {
    await this.delay(1000);
    
    const bookId = `book_${Date.now()}`;
    const task = {
      taskId: `task_${Date.now()}`,
      bookId,
      fileName: file.name,
      fileSize: file.size,
      status: 'PENDING'
    };
    
    setTimeout(() => this.startMockProcessing(task), 500);
    
    return {
      success: true,
      data: {
        bookId,
        taskId: task.taskId,
        fileName: file.name,
        fileSize: file.size,
        status: 'UPLOADING',
        message: '文件上传成功，正在开始处理...'
      }
    };
  }
  
  /**
   * Mock WebSocket设置
   */
  setupMockWebSocket(taskId) {
    this.emit('ws:connected');
    // Mock处理过程会通过emit发送进度更新
  }
  
  /**
   * 开始Mock处理流程
   */
  startMockProcessing(task) {
    const stages = ['FILE_UPLOAD', 'TEXT_PREPROCESS', 'CHAPTER_OUTLINE', 'COARSE_OUTLINE', 'MAIN_OUTLINE', 'WORLD_OUTLINE'];
    let currentStage = 0;
    let progress = 0;
    
    const interval = setInterval(() => {
      const stage = stages[currentStage];
      
      if (stage === 'CHAPTER_OUTLINE' || stage === 'COARSE_OUTLINE' || stage === 'MAIN_OUTLINE') {
        progress += 5;
        if (progress > 100) {
          progress = 0;
          currentStage++;
        }
        
        this.emit('progress', {
          stage,
          progress: progress,
          total: 100,
          completed: Math.floor(progress)
        });
      } else {
        progress += 20;
        if (progress > 100) {
          progress = 0;
          currentStage++;
        }
        
        this.emit('progress', {
          stage,
          progress
        });
      }
      
      if (stage === 'CHAPTER_OUTLINE' && progress === 50) {
        this.emit('outline_update', {
          outlineType: 'CHAPTER',
          outlineId: `outline_ch_${Date.now()}`,
          summary: '本章节讲述了主角在修炼道路上的重要突破...',
          status: 'completed'
        });
      }
      
      if (currentStage >= stages.length) {
        clearInterval(interval);
        this.emit('completed', {
          bookId: task.bookId,
          status: 'completed'
        });
      }
    }, 500);
  }
  
  /**
   * Mock获取书籍列表
   */
  mockGetBooks() {
    return {
      success: true,
      data: {
        books: [
          {
            bookId: 'book_001',
            title: '示例小说1',
            originalName: 'novel1.txt',
            fileType: 'TXT',
            totalChapters: 100,
            status: 'COMPLETED',
            createdAt: new Date().toISOString()
          },
          {
            bookId: 'book_002',
            title: '示例小说2',
            originalName: 'novel2.epub',
            fileType: 'EPUB',
            totalChapters: 50,
            status: 'PROCESSING',
            createdAt: new Date().toISOString()
          }
        ],
        pagination: { page: 1, pageSize: 20, total: 2, totalPages: 1 }
      }
    };
  }
  
  /**
   * Mock获取书籍详情
   */
  mockGetBook(bookId) {
    return {
      success: true,
      data: {
        bookId,
        title: '示例小说',
        originalName: 'novel.txt',
        fileType: 'TXT',
        totalChapters: 100,
        status: 'COMPLETED',
        createdAt: new Date().toISOString()
      }
    };
  }
  
  /**
   * Mock获取纲树
   */
  mockGetOutlineTree(bookId) {
    return {
      success: true,
      data: {
        bookId,
        tree: {
          outlineId: 'world_001',
          outlineType: 'WORLD',
          label: '世界纲',
          summary: '这是一个宏大的修仙世界...',
          status: 'completed',
          children: [
            {
              outlineId: 'main_001',
              outlineType: 'MAIN',
              label: '大纲 1 (章节1-100)',
              summary: '第一部分：主角的成长历程...',
              status: 'completed',
              children: [
                {
                  outlineId: 'coarse_001',
                  outlineType: 'COARSE',
                  label: '粗纲 1-1 (章节1-10)',
                  summary: '开篇：主角觉醒...',
                  status: 'completed',
                  children: [
                    {
                      outlineId: 'chapter_001',
                      outlineType: 'CHAPTER',
                      label: '章纲 1',
                      summary: '第一章讲述了主角的背景介绍...',
                      status: 'completed'
                    },
                    {
                      outlineId: 'chapter_002',
                      outlineType: 'CHAPTER',
                      label: '章纲 2',
                      summary: '第二章描述主角的初次修炼...',
                      status: 'completed'
                    }
                  ]
                }
              ]
            }
          ]
        }
      }
    };
  }
  
  /**
   * Mock获取纲详情
   */
  mockGetOutline(outlineId) {
    const types = {
      'world': '世界纲',
      'main': '大纲',
      'coarse': '粗纲',
      'chapter': '章纲'
    };
    
    const prefix = outlineId.split('_')[0];
    const content = {
      summary: '这是纲的概括内容...',
      details: '这里是详细的纲内容，包括剧情分析、人物设定、节奏把控等方面...',
      metadata: {
        wordCount: 2000,
        createdAt: new Date().toISOString()
      }
    };
    
    return {
      success: true,
      outline: {
        outlineId,
        outlineType: prefix.toUpperCase(),
        label: types[prefix] || '未知类型',
        status: 'completed',
        content
      }
    };
  }
  
  /**
   * 工具方法：延迟
   */
  delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
  
  // ================================
  // 便捷方法（供 app.js 使用）
  // ================================
  
  /**
   * 启用 Mock 模式
   */
  enableMockMode() {
    this.mockMode = true;
  }
  
  /**
   * 禁用 Mock 模式
   */
  disableMockMode() {
    this.mockMode = false;
  }

  normalizeStatus(status) {
    const statusMap = {
      IDLE: 'idle',
      PROCESSING: 'processing',
      COMPLETED: 'completed',
      ERROR: 'error',
      FAILED: 'failed',
      PENDING: 'pending',
      UPLOADING: 'uploading',
      idle: 'idle',
      processing: 'processing',
      completed: 'completed',
      error: 'error',
      failed: 'failed',
      pending: 'pending',
      uploading: 'uploading'
    };

    return statusMap[status] || 'pending';
  }

  normalizeBook(book = {}) {
    return {
      ...book,
      id: book.id || book.bookId || '',
      title: book.title || book.originalName || '未命名书籍',
      author: book.author || '未知',
      description: book.description || '',
      status: this.normalizeStatus(book.status),
      createdAt: book.createdAt || new Date().toISOString()
    };
  }
  
  /**
   * 上传书籍
   */
  async uploadBook(file, bookInfo) {
    if (this.mockMode) {
      const res = await this.mockFileUpload(file, bookInfo);
      return res.data || res;
    }
    return this.uploadFile(file, bookInfo).then(res => res.data);
  }
  
  /**
   * 获取书籍列表
   */
  async getBookList() {
    if (this.mockMode) {
      const res = this.mockGetBooks();
      const books = res.data?.books || res.books || [];
      return books.map(book => this.normalizeBook(book));
    }
    return this.get('/books').then(res => {
      const books = res.data?.books || res.books || [];
      return books.map(book => this.normalizeBook(book));
    });
  }
  
  async getBookDetail(bookId) {
    if (this.mockMode) {
      const res = this.mockGetBook(bookId);
      return this.normalizeBook(res.data || res.book || res);
    }
    return this.get(`/books/${bookId}`).then(res => this.normalizeBook(res.data || res.book || res));
  }
  
  /**
   * 删除书籍
   */
  async deleteBook(bookId) {
    if (this.mockMode) {
      return { success: true };
    }
    return this.delete(`/books/${bookId}`);
  }
  
  /**
   * 获取纲树结构
   */
  async getOutlineTree(bookId) {
    if (this.mockMode) {
      const res = this.mockGetOutlineTree(bookId);
      return res.data || res;
    }
    return this.get(`/books/${bookId}/tree`).then(res => {
      if (res.data && res.data.tree) return res.data;
      if (res.tree) return res;
      return res;
    });
  }
  
  /**
   * 获取处理状态
   */
  async getProcessingStatus(bookId) {
    if (this.mockMode) {
      return { status: 'completed', progress: 100 };
    }
    return this.get(`/books/${bookId}/status`).then(res => res.data);
  }
}

// API接口定义
const API = {
  // 书籍相关
  books: {
    list: () => api.get('/books').then(res => res.data || res),
    get: (bookId) => api.get(`/books/${bookId}`).then(res => res.data || res),
    upload: (file, options) => api.uploadFile(file, options),
    delete: (bookId) => api.delete(`/books/${bookId}`)
  },
  
  // 纲相关
  outlines: {
    getTree: (bookId) => api.get(`/books/${bookId}/tree`).then(res => res.data || res),
    getDetail: (outlineId) => api.get(`/outlines/${outlineId}`).then(res => res.data || res),
    copy: (outlineId, format = 'text') => api.post(`/outlines/${outlineId}/copy?format=${format}`)
  },
  
  // 任务相关
  tasks: {
    getStatus: (taskId) => api.get(`/tasks/${taskId}`).then(res => res.data || res),
    getErrors: (taskId) => api.get(`/tasks/${taskId}/errors`).then(res => res.data || res)
  }
};

// 创建默认实例（默认连接后端，不启用mock）
const api = new APIClient({ mockMode: false });

// 导出
export { APIClient, API, api };
export default api;
