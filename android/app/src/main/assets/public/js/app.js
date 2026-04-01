
/**
 * AI小说拆书系统 - 主应用入口
 * 整合状态管理、API客户端、UI组件
 * @version 1.0.0
 */

// 导入模块
import { StateManager } from './state.js';
import { APIClient } from './api.js';
import { FileUploader, ProgressMonitor, ToastManager } from './components.js';

/**
 * 应用主类
 */
class NovelPlatformApp {
    constructor() {
        // 状态管理器单例
        this.state = StateManager.getInstance();
        
        // API客户端
        this.api = null;
        
        // 组件实例
        this.uploader = null;
        this.progressMonitor = null;
        this.toastManager = null;
        
        // 当前页面
        this.currentPage = 'upload';
        
        // 绑定方法
        this.init = this.init.bind(this);
        this.handleStartProcess = this.handleStartProcess.bind(this);
        this.handleReset = this.handleReset.bind(this);
        this.toggleTheme = this.toggleTheme.bind(this);
        this.handleSearch = this.handleSearch.bind(this);
        this.handleFilter = this.handleFilter.bind(this);
        this.saveSettings = this.saveSettings.bind(this);
        this.resetSettings = this.resetSettings.bind(this);
    }
    
    /**
     * 初始化应用
     */
    async init() {
        try {
            console.log('[App] 初始化AI小说拆书系统...');
            
            // 初始化Toast管理器（ToastManager无参数构造，自动创建容器）
            this.toastManager = window.toast || new ToastManager();
            window.toastManager = this.toastManager; // 全局访问
            this.toastManager.info('系统初始化中...');
            
            // 加载保存的设置
            this.loadSettings();
            
            // 初始化API客户端
            await this.initAPI();
            
            // 初始化组件
            this.initComponents();
            
            // 绑定事件
            this.bindEvents();
            
            // 订阅状态变化
            this.subscribeToState();
            
            console.log('[App] 初始化完成');
            this.toastManager.success('系统就绪');
        } catch (error) {
            console.error('[App] 初始化失败:', error);
            this.toastManager?.error('初始化失败: ' + error.message);
        }
    }
    
    /**
     * 初始化API客户端
     */
    async initAPI() {
        const settings = this.state.get('settings') || {};
        const apiConfig = {
            baseUrl: settings.apiBaseUrl || 'http://localhost:8000/api/v1',
            mockMode: settings.mockMode !== false
        };
        
        this.api = new APIClient(apiConfig);
        
        if (apiConfig.mockMode) {
            console.log('[App] API Mock模式已启用');
        } else {
            console.log('[App] API 真实模式已启用，连接后端: ' + apiConfig.baseUrl);
        }
        
        // 设置事件回调（使用on方法订阅事件）
        this.api.on('progress', (data) => {
            const stageMapping = {
                'FILE_UPLOAD': 'fileUpload',
                'TEXT_PREPROCESS': 'textPreprocess',
                'CHAPTER_OUTLINE': 'chapterOutline',
                'COARSE_OUTLINE': 'coarseOutline',
                'MAIN_OUTLINE': 'mainOutline',
                'WORLD_OUTLINE': 'worldOutline'
            };
            const stage = stageMapping[data.stage] || data.stage;
            this.state.set('processingStatus.currentStage', stage);
            this.state.set('processingStatus.progress', data.progress);
            if (stage) {
                this.state.set(`processingStatus.${stage}.progress`, data.progress);
                this.state.set(`processingStatus.${stage}.status`, data.progress >= 100 ? 'completed' : 'active');
            }
        });
        
        this.api.on('error', (error) => {
            this.toastManager.error('处理错误: ' + (error.message || error));
            this.state.set('processingStatus.isProcessing', false);
        });
        
        this.api.on('completed', (result) => {
            this.toastManager.success('处理完成！');
            this.state.set('processingStatus.isProcessing', false);
            this.state.set('processingStatus.result', result);
            this.state.set('currentBook', {
                id: result.bookId,
                status: 'completed',
                createdAt: new Date().toISOString()
            });
            this.navigateTo('detail');
        });
        
        this.api.on('outline_update', (payload) => {
            const typeMapping = {
                'CHAPTER': 'chapterOutline',
                'COARSE': 'coarseOutline',
                'MAIN': 'mainOutline',
                'WORLD': 'worldOutline'
            };
            const stage = typeMapping[payload.outlineType];
            if (stage) {
                this.state.set(`processingStatus.${stage}.lastUpdate`, payload);
            }
        });
        
        this.api.on('ws:connected', () => {
            this.state.set('wsConnected', true);
        });
        
        this.api.on('ws:disconnected', () => {
            this.state.set('wsConnected', false);
        });
        
        this.api.on('ws:error', () => {
            this.state.set('wsConnected', false);
        });
    }
    
    /**
     * 初始化UI组件
     */
    initComponents() {
        // 文件上传组件
    const uploaderContainer = document.getElementById('fileUploader');
    this.uploader = new FileUploader(uploaderContainer, {
      acceptedFormats: ['.epub', '.txt', '.doc', '.docx', '.pdf'],
      maxFileSize: 50 * 1024 * 1024, // 50MB
      onUpload: (file) => {
        this.handleFileSelect(file);
      },
      onError: (title, message) => {
        this.handleFileError({ title, message });
      }
    });
        
        // 进度监控组件（ProgressMonitor构造参数：container, options）
        const progressContainer = document.getElementById('progressMonitor');
        this.progressMonitor = new ProgressMonitor(progressContainer);
    }
    
    /**
     * 绑定事件监听
     */
    bindEvents() {
        // 页面导航
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const page = e.currentTarget.dataset.page;
                this.navigateTo(page);
            });
        });
        
        // 开始处理按钮
        const btnStartProcess = document.getElementById('btnStartProcess');
        if (btnStartProcess) {
            btnStartProcess.addEventListener('click', this.handleStartProcess);
        }
        
        // 重置按钮
        const btnReset = document.getElementById('btnReset');
        if (btnReset) {
            btnReset.addEventListener('click', this.handleReset);
        }
        
        // 返回书库按钮
        const btnBackToLibrary = document.getElementById('btnBackToLibrary');
        if (btnBackToLibrary) {
            btnBackToLibrary.addEventListener('click', () => this.navigateTo('library'));
        }
        
        // 设置页面事件
        this.bindSettingsEvents();
        
        // Tab切换事件
        this.bindTabEvents();
        
        // 主题切换
        const themeToggle = document.getElementById('themeToggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', this.toggleTheme);
        }
        
        // 搜索和过滤
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.addEventListener('input', this.handleSearch);
        }
        
        const statusFilter = document.getElementById('statusFilter');
        if (statusFilter) {
            statusFilter.addEventListener('change', this.handleFilter);
        }
    }
    
    /**
     * 绑定设置页面事件
     */
    bindSettingsEvents() {
        // Temperature滑块
        const tempSlider = document.getElementById('temperature');
        const tempValue = document.getElementById('temperatureValue');
        if (tempSlider && tempValue) {
            tempSlider.addEventListener('input', () => {
                tempValue.textContent = tempSlider.value;
            });
        }
        
        // API Key显示/隐藏
        const toggleApiKey = document.getElementById('toggleApiKey');
        const apiKeyInput = document.getElementById('apiKey');
        if (toggleApiKey && apiKeyInput) {
            toggleApiKey.addEventListener('click', () => {
                const type = apiKeyInput.type === 'password' ? 'text' : 'password';
                apiKeyInput.type = type;
                const icon = toggleApiKey.querySelector('i');
                icon.className = type === 'password' ? 'fas fa-eye' : 'fas fa-eye-slash';
            });
        }
        
        // 保存设置
        const btnSaveSettings = document.getElementById('btnSaveSettings');
        if (btnSaveSettings) {
            btnSaveSettings.addEventListener('click', this.saveSettings);
        }
        
        // 重置设置
        const btnResetSettings = document.getElementById('btnResetSettings');
        if (btnResetSettings) {
            btnResetSettings.addEventListener('click', this.resetSettings);
        }
    }
    
    /**
     * 绑定Tab切换事件
     */
    bindTabEvents() {
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const tabId = btn.dataset.tab;
                const container = btn.closest('.outline-container');
                
                // 切换按钮状态
                container.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                
                // 切换内容
                container.querySelectorAll('.tab-content').forEach(content => {
                    content.classList.remove('active');
                });
                const activeContent = container.querySelector(`#tab-${tabId}`);
                if (activeContent) {
                    activeContent.classList.add('active');
                }
            });
        });
    }
    
    /**
     * 订阅状态变化
     */
    subscribeToState() {
        // 监听处理状态变化
        this.state.subscribe('processingStatus', (status) => {
            if (this.progressMonitor) {
                this.progressMonitor.update(status);
            }
        });
        
        // 监听书籍列表变化
        this.state.subscribe('books', (books) => {
            this.renderBookList(books);
        });
        
        // 监听当前书籍变化
        this.state.subscribe('currentBook', (book) => {
            if (book) {
                this.renderBookDetail(book);
            }
        });
    }
    
    /**
     * 页面导航
     */
    navigateTo(page) {
        // 更新导航状态
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.toggle('active', link.dataset.page === page);
        });
        
        // 切换页面
        document.querySelectorAll('.page').forEach(p => {
            p.classList.remove('active');
        });
        
        const targetPage = document.getElementById(`page-${page}`);
        if (targetPage) {
            targetPage.classList.add('active');
            this.currentPage = page;
        }
        
        // 页面特殊逻辑
        if (page === 'library') {
            this.loadBookList();
        }
        
        if (page === 'settings') {
            this.loadSettings();
        }
        
        console.log('[App] 导航到页面:', page);
    }
    
    /**
     * 处理文件选择
     */
    handleFileSelect(file) {
        // 解析文件名作为默认书名
        const fileName = file.name.replace(/\.[^/.]+$/, '');
        document.getElementById('bookTitle').value = fileName;
        
        // 显示书籍信息表单
        document.getElementById('bookInfoForm').classList.remove('hidden');
        
        // 保存文件到状态
        this.state.set('currentFile', {
            file: file,
            name: file.name,
            size: file.size,
            type: file.type || this.getFileType(file.name)
        });
        
        this.toastManager.success(`已选择文件: ${file.name}`);
        console.log('[App] 文件已选择:', file.name);
    }
    
    /**
     * 处理文件错误
     */
    handleFileError(error) {
        this.toastManager.error(`文件错误: ${error.message}`);
    }
    
    /**
     * 获取文件类型
     */
    getFileType(filename) {
        const ext = filename.split('.').pop().toLowerCase();
        const typeMap = {
            'epub': 'application/epub+zip',
            'txt': 'text/plain',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'pdf': 'application/pdf'
        };
        return typeMap[ext] || 'application/octet-stream';
    }
    
    /**
     * 开始处理
     */
    async handleStartProcess() {
        const file = this.state.get('currentFile');
        if (!file) {
            this.toastManager.warning('请先选择文件');
            return;
        }
        
        const bookInfo = {
            title: document.getElementById('bookTitle').value || file.name,
            author: document.getElementById('bookAuthor').value || '未知',
            description: document.getElementById('bookDescription').value || ''
        };
        
        // 更新状态
        this.state.set('processingStatus', {
            isProcessing: true,
            currentStage: 'fileUpload',
            progress: 0,
            fileUpload: { status: 'active', progress: 0 },
            textPreprocess: { status: 'pending', progress: 0 },
            chapterOutline: { status: 'pending', progress: 0, total: 0, completed: 0 },
            coarseOutline: { status: 'pending', progress: 0, total: 0, completed: 0 },
            mainOutline: { status: 'pending', progress: 0, total: 0, completed: 0 },
            worldOutline: { status: 'pending', progress: 0 }
        });
        
        // 显示进度区域
        document.getElementById('progressSection').classList.remove('hidden');
        
        // 禁用开始按钮
        const btn = document.getElementById('btnStartProcess');
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 处理中...';
        
        try {
            // 开始处理的API调用
            this.toastManager.info('开始处理，请等待...');
            
            // 调用API上传并处理
            const result = await this.api.uploadBook(file.file, bookInfo);      

            if (this.api.mockMode) {
                await this.simulateProgress();
                const mockBook = {
                    id: result.bookId || 'mock-' + Date.now(),
                    ...bookInfo,
                    status: 'completed',
                    createdAt: new Date().toISOString(),
                    outline: {
                        worldOutline: {
                            outlineId: 'world_mock_001',
                            title: '世界纲',
                            name: '世界纲',
                            summary: '这是一个宏大的修仙世界...',
                            content: '这是一个宏大的修仙世界，主角从平凡走向巅峰...'
                        },
                        mainOutline: [
                            {
                                outlineId: 'main_mock_001',
                                title: '大纲 1',
                                name: '大纲 1',
                                summary: '第一部分：主角的成长历程...',
                                content: '主角从一个普通少年开始修炼...'
                            }
                        ],
                        coarseOutline: [
                            {
                                outlineId: 'coarse_mock_001',
                                title: '粗纲 1-1',
                                name: '粗纲 1-1',
                                summary: '开篇：主角觉醒...',
                                content: '故事开篇，主角在小镇中觉醒修炼天赋...'
                            }
                        ],
                        chapterOutline: [
                            {
                                outlineId: 'chapter_mock_001',
                                title: '章纲 1',
                                name: '章纲 1',
                                summary: '第一章讲述了主角的背景介绍...',
                                content: '第一章详细描述了主角的出身和成长环境...'
                            },
                            {
                                outlineId: 'chapter_mock_002',
                                title: '章纲 2',
                                name: '章纲 2',
                                summary: '第二章描述主角的初次修炼...',
                                content: '第二章描述了主角初次接触修炼功法...'
                            }
                        ]
                    }
                };
                this.state.set('currentBook', mockBook);
                this.toastManager.success('处理完成！');
                setTimeout(() => {
                    this.navigateTo('detail');
                }, 1000);
            } else if (result.taskId) {
                this.state.set('currentBook', {
                    id: result.bookId,
                    ...bookInfo,
                    status: 'processing',
                    createdAt: new Date().toISOString()
                });
                this.api.connectWebSocket(result.taskId);
                this.pollProcessingStatus(result.bookId);
            }
        } catch (error) {
            console.error('[App] 处理失败:', error);
            this.toastManager.error('处理失败: ' + error.message);
            this.state.set('processingStatus.isProcessing', false);
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-play"></i> 开始处理';
        }
    }
    
    /**
     * 模拟进度更新
     */
    async simulateProgress() {
        const stages = ['FILE_UPLOAD', 'TEXT_PREPROCESS', 'CHAPTER_OUTLINE', 'COARSE_OUTLINE', 'MAIN_OUTLINE', 'WORLD_OUTLINE'];
        const stageMapping = {
            'FILE_UPLOAD': 'fileUpload',
            'TEXT_PREPROCESS': 'textPreprocess',
            'CHAPTER_OUTLINE': 'chapterOutline',
            'COARSE_OUTLINE': 'coarseOutline',
            'MAIN_OUTLINE': 'mainOutline',
            'WORLD_OUTLINE': 'worldOutline'
        };
        
        for (let i = 0; i < stages.length; i++) {
            const backendStage = stages[i];
            const stage = stageMapping[backendStage];
            
            if (i > 0) {
                this.state.set(`processingStatus.${stageMapping[stages[i - 1]]}.status`, 'completed');
            }
            
            this.state.set('processingStatus.currentStage', stage);
            this.state.set(`processingStatus.${stage}.status`, 'active');
            
            for (let p = 0; p <= 100; p += 20) {
                this.state.set(`processingStatus.${stage}.progress`, p);
                this.state.set('processingStatus.progress', Math.round(((i * 100) + p) / stages.length));
                
                await new Promise(resolve => setTimeout(resolve, 200));
            }
        }
        
        this.state.set(`processingStatus.${stageMapping[stages[stages.length - 1]]}.status`, 'completed');
        this.state.set('processingStatus.isProcessing', false);
    }

    async pollProcessingStatus(bookId) {
        const maxPolls = 300;
        let pollCount = 0;

        const poll = async () => {
            if (pollCount >= maxPolls) return;
            pollCount++;

            try {
                const status = await this.api.getProcessingStatus(bookId);
                if (!status) return;

                const stageMapping = {
                    'FILE_UPLOAD': 'fileUpload',
                    'TEXT_PREPROCESS': 'textPreprocess',
                    'CHAPTER_OUTLINE': 'chapterOutline',
                    'COARSE_OUTLINE': 'coarseOutline',
                    'MAIN_OUTLINE': 'mainOutline',
                    'WORLD_OUTLINE': 'worldOutline'
                };

                if (status.currentStage) {
                    const stage = stageMapping[status.currentStage];
                    if (stage) {
                        this.state.set('processingStatus.currentStage', stage);
                        this.state.set(`processingStatus.${stage}.status`, 'active');
                    }
                }

                if (status.stageProgress) {
                    for (const [backendStage, progress] of Object.entries(status.stageProgress)) {
                        const stage = stageMapping[backendStage];
                        if (stage) {
                            this.state.set(`processingStatus.${stage}.progress`, progress);
                            if (progress >= 100) {
                                this.state.set(`processingStatus.${stage}.status`, 'completed');
                            }
                        }
                    }
                }

                const bookStatus = this.api.normalizeStatus(status.status);
                if (bookStatus === 'completed' || bookStatus === 'error') {
                    this.state.set('processingStatus.isProcessing', false);
                    const currentBook = this.state.get('currentBook') || {};
                    currentBook.id = bookId;
                    currentBook.status = bookStatus;
                    currentBook.createdAt = new Date().toISOString();
                    if (bookStatus === 'completed') {
                        try {
                            const treeData = await this.api.getOutlineTree(bookId);
                            if (treeData && treeData.tree) {
                                currentBook.outline = this.parseOutlineTree(treeData.tree);
                            }
                        } catch (e) {
                            console.warn('[App] 处理完成后纲树加载失败:', e);
                        }
                        this.toastManager.success('处理完成！');
                    } else {
                        this.toastManager.error('处理失败');
                    }
                    this.state.set('currentBook', currentBook);
                    if (bookStatus === 'completed') {
                        this.navigateTo('detail');
                    }
                    return;
                }
            } catch (e) {
                console.error('[App] 轮询状态失败:', e);
            }

            setTimeout(poll, 2000);
        };

        poll();
    }
    
    /**
     * 重置上传
     */
    handleReset() {
        this.uploader.reset();
        document.getElementById('bookInfoForm').classList.add('hidden');
        document.getElementById('progressSection').classList.add('hidden');
        document.getElementById('bookTitle').value = '';
        document.getElementById('bookAuthor').value = '';
        document.getElementById('bookDescription').value = '';
        
        this.state.delete('currentFile');
        this.state.set('processingStatus', {
            isProcessing: false,
            currentStage: null,
            progress: 0,
            fileUpload: { status: 'pending', progress: 0 },
            textPreprocess: { status: 'pending', progress: 0 },
            chapterOutline: { status: 'pending', progress: 0, total: 0, completed: 0 },
            coarseOutline: { status: 'pending', progress: 0, total: 0, completed: 0 },
            mainOutline: { status: 'pending', progress: 0, total: 0, completed: 0 },
            worldOutline: { status: 'pending', progress: 0 }
        });
        
        this.toastManager.info('已重置');
    }
    
    /**
     * 加载书籍列表
     */
    async loadBookList() {
        try {
            const books = await this.api.getBookList();
            this.state.set('books', books);
        } catch (error) {
            console.error('[App] 加载书库失败:', error);
            this.toastManager.error('加载书库失败');
        }
    }
    
    /**
     * 渲染书籍列表
     */
    renderBookList(books) {
        const grid = document.getElementById('bookGrid');
        if (!grid) return;
        
        if (!books || books.length === 0) {
            grid.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-books"></i>
                    <p>暂无书籍，快去上传吧！</p>
                </div>
            `;
            return;
        }
        
        grid.innerHTML = books.map(book => `
            <div class="book-card" data-id="${book.id}">
                <div class="book-cover">
                    <i class="fas fa-book"></i>
                </div>
                <div class="book-info">
                    <h4>${book.title}</h4>
                    <p class="book-author">${book.author}</p>
                    <div class="book-status ${book.status}">
                        ${this.getStatusText(book.status)}
                    </div>
                </div>
                <div class="book-actions">
                    <button class="btn btn-sm btn-primary" onclick="app.viewBookDetail('${book.id}')">
                        <i class="fas fa-eye"></i> 查看
                    </button>
                    <button class="btn btn-sm btn-ghost" onclick="app.deleteBook('${book.id}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `).join('');
    }
    
    /**
     * 获取状态文本
     */
    getStatusText(status) {
        const statusMap = {
            'completed': '已完成',
            'processing': '处理中',
            'failed': '失败',
            'pending': '等待中',
            'idle': '待处理',
            'error': '出错',
            'uploading': '上传中'
        };
        return statusMap[status] || status;
    }
    
    /**
     * 查看书籍详情
     */
    async viewBookDetail(bookId) {
        try {
            const book = await this.api.getBookDetail(bookId);
            try {
                const treeData = await this.api.getOutlineTree(bookId);
                if (treeData && treeData.tree) {
                    book.outline = this.parseOutlineTree(treeData.tree);
                }
            } catch (treeErr) {
                console.warn('[App] 纲树加载失败:', treeErr);
            }
            this.state.set('currentBook', book);
            this.navigateTo('detail');
        } catch (error) {
            this.toastManager.error('加载书籍失败');
        }
    }

    parseOutlineTree(treeNode) {
        if (!treeNode) return null;
        const result = {};
        const typeMapping = {
            'CHAPTER': 'chapterOutline',
            'COARSE': 'coarseOutline',
            'MAIN': 'mainOutline',
            'WORLD': 'worldOutline'
        };
        this._collectOutlineByType(treeNode, result, typeMapping);
        return result;
    }

    _collectOutlineByType(node, result, typeMapping) {
        const key = typeMapping[node.outlineType];
        if (!key) return;
        const item = {
            outlineId: node.outlineId,
            title: node.label || '',
            name: node.label || '',
            summary: node.summary || '',
            content: node.content || node.summary || '',
            status: node.status
        };
        if (key === 'worldOutline') {
            result.worldOutline = item;
        } else {
            if (!result[key]) result[key] = [];
            result[key].push(item);
        }
        if (node.children && node.children.length > 0) {
            for (const child of node.children) {
                this._collectOutlineByType(child, result, typeMapping);
            }
        }
    }
    
    /**
     * 渲染书籍详情
     */
    renderBookDetail(book) {
        const bookMeta = document.getElementById('bookMeta');
        const outlineTree = document.getElementById('outlineTree');
        const outlineList = document.getElementById('outlineList');
        
        // 渲染元信息
        if (bookMeta) {
            bookMeta.innerHTML = `
                <h2>${book.title}</h2>
                <p class="author"><i class="fas fa-user"></i> ${book.author}</p>
                <p class="description">${book.description || '暂无简介'}</p>
            `;
        }
        
        // 渲染大纲树
        if (outlineTree && book.outline) {
            outlineTree.innerHTML = this.renderOutlineTree(book.outline);
        }
        
        // 渲染列表视图
        if (outlineList && book.outline) {
            outlineList.innerHTML = this.renderOutlineList(book.outline);
        }
    }
    
    /**
     * 渲染大纲树形图
     */
    renderOutlineTree(outline) {
        if (!outline) return '<div class="empty-state"><p>暂无大纲数据</p></div>';
        
        return `
            <ul class="tree-root">
                ${this.renderOutlineNode(Array.isArray(outline.worldOutline) ? outline.worldOutline : (outline.worldOutline ? [outline.worldOutline] : []), 'world', '世界纲')}
                ${this.renderOutlineNode(outline.mainOutline, 'rough', '大纲')}
                ${this.renderOutlineNode(outline.coarseOutline, 'coarse', '粗纲')}
                ${this.renderOutlineNode(outline.chapterOutline, 'chapter', '章纲')}
            </ul>
        `;
    }
    
    /**
     * 渲染大纲节点
     */
    renderOutlineNode(items, type, label) {
        if (!items || items.length === 0) return '';
        
        return `
            <li class="tree-node ${type}">
                <div class="node-header">
                    <span class="node-icon"><i class="fas fa-${this.getNodeIcon(type)}"></i></span>
                    <span class="node-label">${label}</span>
                    <span class="node-count">${items.length}个</span>
                </div>
                <ul class="tree-children">
                    ${items.map((item, index) => `
                        <li class="tree-leaf" data-type="${type}" data-index="${index}">
                            <div class="leaf-content" onclick="app.showOutlineDetail('${type}', ${index})">
                                <span class="leaf-title">${item.title || item.name || '未命名'}</span>
                                <span class="leaf-summary">${item.summary || ''}</span>
                            </div>
                            <button class="copy-btn-small" onclick="event.stopPropagation(); app.copyOutlineContent('${type}', ${index})" title="复制内容">
                                <i class="fas fa-copy"></i>
                            </button>
                        </li>
                    `).join('')}
                </ul>
            </li>
        `;
    }
    
    /**
     * 显示大纲详情
     */
    showOutlineDetail(type, index) {
        const book = this.state.get('currentBook');
        if (!book || !book.outline) {
            this.toastManager.warning('暂无大纲数据');
            return;
        }
        
        let outlineData = null;
        if (type === 'chapter') {
            outlineData = book.outline.chapterOutline;
        } else if (type === 'coarse') {
            outlineData = book.outline.coarseOutline;
        } else if (type === 'rough') {
            outlineData = book.outline.mainOutline;
        } else if (type === 'world') {
            outlineData = [book.outline.worldOutline];
        }
        
        if (!outlineData || !outlineData[index]) {
            this.toastManager.warning('未找到该大纲数据');
            return;
        }
        
        const item = outlineData[index];
        this.showDetailModal(type, index, item);
    }
    
    /**
     * 显示详情模态框
     */
    showDetailModal(type, index, item) {
        const typeLabels = {
            'chapter': '章纲',
            'coarse': '粗纲',
            'rough': '大纲',
            'world': '世界纲'
        };
        
        const modalContainer = document.getElementById('modalContainer');
        if (!modalContainer) return;
        
        const content = item.content || item;
        const contentStr = typeof content === 'object' ? JSON.stringify(content, null, 2) : String(content);
        
        modalContainer.innerHTML = `
            <div class="modal-overlay open" onclick="app.closeDetailModal(event)">
                <div class="modal" onclick="event.stopPropagation()">
                    <div class="modal-header">
                        <h3 class="modal-title">${typeLabels[type] || '大纲'} #${index + 1}</h3>
                        <button class="modal-close" onclick="app.closeDetailModal()">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    <div class="modal-body">
                        <div class="detail-section">
                            <h4 class="detail-section-title">标题</h4>
                            <p>${item.title || item.name || '未命名'}</p>
                        </div>
                        ${item.summary ? `
                        <div class="detail-section">
                            <h4 class="detail-section-title">概括</h4>
                            <p>${item.summary}</p>
                        </div>
                        ` : ''}
                        <div class="detail-section">
                            <h4 class="detail-section-title">详细内容</h4>
                            <pre class="detail-content-json">${this.escapeHtml(contentStr)}</pre>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" onclick="app.closeDetailModal()">关闭</button>
                        <button class="btn btn-primary" onclick="app.copyOutlineContent('${type}', ${index})">
                            <i class="fas fa-copy"></i> 复制内容
                        </button>
                    </div>
                </div>
            </div>
        `;
    }
    
    /**
     * 关闭详情模态框
     */
    closeDetailModal(event) {
        if (event && event.target !== event.currentTarget) return;
        const modalContainer = document.getElementById('modalContainer');
        if (modalContainer) {
            modalContainer.innerHTML = '';
        }
    }
    
    /**
     * 转义HTML
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    /**
     * 复制大纲内容
     */
    async copyOutlineContent(type, index) {
        const book = this.state.get('currentBook');
        if (!book || !book.outline) {
            this.toastManager.warning('暂无大纲数据');
            return;
        }
        
        let outlineData = null;
        if (type === 'chapter') {
            outlineData = book.outline.chapterOutline;
        } else if (type === 'coarse') {
            outlineData = book.outline.coarseOutline;
        } else if (type === 'rough') {
            outlineData = book.outline.mainOutline;
        } else if (type === 'world') {
            outlineData = [book.outline.worldOutline];
        }
        
        if (!outlineData || !outlineData[index]) {
            this.toastManager.error('未找到该大纲数据');
            return;
        }
        
        const item = outlineData[index];
        const content = item.content || item;
        const contentStr = typeof content === 'object' ? JSON.stringify(content, null, 2) : String(content);
        
        const typeLabels = {
            'chapter': '章纲',
            'coarse': '粗纲',
            'rough': '大纲',
            'world': '世界纲'
        };
        
        let copyText = `【${typeLabels[type]} #${index + 1}】\n`;
        copyText += `标题：${item.title || item.name || '未命名'}\n`;
        if (item.summary) {
            copyText += `概括：${item.summary}\n`;
        }
        copyText += `\n详细内容：\n${contentStr}`;
        
        try {
            if (navigator.clipboard && navigator.clipboard.writeText) {
                await navigator.clipboard.writeText(copyText);
            } else {
                const textarea = document.createElement('textarea');
                textarea.value = copyText;
                textarea.style.position = 'fixed';
                textarea.style.left = '-9999px';
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);
            }
            this.toastManager.success('内容已复制到剪贴板');
        } catch (err) {
            console.error('[App] 复制失败:', err);
            this.toastManager.error('复制失败，请手动复制');
        }
    }
    
    /**
     * 获取节点图标
     */
    getNodeIcon(type) {
        const iconMap = {
            'world': 'globe',
            'rough': 'sitemap',
            'coarse': 'list',
            'chapter': 'file-alt'
        };
        return iconMap[type] || 'circle';
    }
    
    /**
     * 渲染大纲列表视图
     */
    renderOutlineList(outline) {
        if (!outline) return '<div class="empty-state"><p>暂无大纲数据</p></div>';
        
        let html = '';
        
        const sections = [
            { key: 'worldOutline', title: '世界纲', wrap: true },
            { key: 'mainOutline', title: '大纲' },
            { key: 'coarseOutline', title: '粗纲' },
            { key: 'chapterOutline', title: '章纲' }
        ];
        for (const sec of sections) {
            let items = outline[sec.key];
            if (!items) continue;
            if (sec.wrap && !Array.isArray(items)) items = [items];
            if (!Array.isArray(items) || items.length === 0) continue;
            html += `<div class="outline-section"><h3>${sec.title}</h3>`;
            html += items.map((c, i) => `
                <div class="outline-item">
                    <div class="item-number">${i + 1}</div>
                    <div class="item-content">
                        <h4>${c.title || c.name || '未命名'}</h4>
                        <p>${c.summary || ''}</p>
                    </div>
                </div>
            `).join('');
            html += '</div>';
        }
        
        return html || '<div class="empty-state"><p>暂无大纲数据</p></div>';
    }
    
    /**
     * 删除书籍
     */
    async deleteBook(bookId) {
        if (!confirm('确定要删除这本书吗？')) return;
        
        try {
            await this.api.deleteBook(bookId);
            this.toastManager.success('删除成功');
            this.loadBookList();
        } catch (error) {
            this.toastManager.error('删除失败');
        }
    }
    
    /**
     * 搜索处理
     */
    handleSearch(e) {
        const query = e.target.value.toLowerCase().trim();
        const allBooks = this.state.get('books') || [];
        if (!query) {
            this.renderBookList(allBooks);
            return;
        }
        const filtered = allBooks.filter(book =>
            (book.title || '').toLowerCase().includes(query) ||
            (book.author || '').toLowerCase().includes(query) ||
            (book.originalName || '').toLowerCase().includes(query)
        );
        this.renderBookList(filtered);
    }
    
    handleFilter(e) {
        const status = e.target.value;
        const allBooks = this.state.get('books') || [];
        if (!status || status === 'all') {
            this.renderBookList(allBooks);
            return;
        }
        const filtered = allBooks.filter(book => book.status === status);
        this.renderBookList(filtered);
    }
    
    /**
     * 主题切换
     */
    toggleTheme() {
        document.body.classList.toggle('dark-theme');
        const isDark = document.body.classList.contains('dark-theme');
        this.state.set('settings.darkTheme', isDark);
        
        const icon = document.querySelector('#themeToggle i');
        if (icon) {
            icon.className = isDark ? 'fas fa-sun' : 'fas fa-moon';
        }
        
        this.toastManager.info(isDark ? '已切换到暗色主题' : '已切换到亮色主题');
    }
    
    /**
     * 加载设置
     */
    loadSettings() {
        try {
            const saved = localStorage.getItem('novel-platform-settings');
            const settings = {
                apiBaseUrl: 'http://localhost:8000/api/v1',
                apiKey: '',
                modelName: 'gpt-5.4-nano',
                temperature: 0.7,
                maxTokens: 4096,
                chapterSize: 2000,
                mockMode: true,
                debugMode: false,
                keepParagraphComplete: true,
                darkTheme: false,
                ...(saved ? JSON.parse(saved) : {})
            };
            
            this.state.set('settings', { ...this.state.get('settings'), ...settings });
            
            const apiBaseUrl = document.getElementById('apiBaseUrl');
            const apiKey = document.getElementById('apiKey');
            const modelName = document.getElementById('modelName');
            const temperature = document.getElementById('temperature');
            const temperatureValue = document.getElementById('temperatureValue');
            const maxTokens = document.getElementById('maxTokens');
            const chapterSize = document.getElementById('chapterSize');
            const mockMode = document.getElementById('mockMode');
            const debugMode = document.getElementById('debugMode');
            const keepParagraphComplete = document.getElementById('keepParagraphComplete');
            
            if (apiBaseUrl) apiBaseUrl.value = settings.apiBaseUrl;
            if (apiKey) apiKey.value = settings.apiKey;
            if (modelName) modelName.value = settings.modelName;
            if (temperature) temperature.value = settings.temperature;
            if (temperatureValue) temperatureValue.textContent = String(settings.temperature);
            if (maxTokens) maxTokens.value = settings.maxTokens;
            if (chapterSize) chapterSize.value = settings.chapterSize;
            if (mockMode) mockMode.checked = settings.mockMode !== false;
            if (debugMode) debugMode.checked = settings.debugMode === true;
            if (keepParagraphComplete) keepParagraphComplete.checked = settings.keepParagraphComplete !== false;
            
            document.body.classList.toggle('dark-theme', settings.darkTheme === true);
            console.log('[App] 已加载设置');
        } catch (error) {
            console.error('[App] 加载设置失败:', error);
        }
    }
    
    /**
     * 保存设置
     */
    saveSettings() {
        try {
            const settings = {
                apiBaseUrl: document.getElementById('apiBaseUrl').value,
                apiKey: document.getElementById('apiKey').value,
                modelName: document.getElementById('modelName').value,
                temperature: parseFloat(document.getElementById('temperature').value),
                maxTokens: parseInt(document.getElementById('maxTokens').value),
                chapterSize: parseInt(document.getElementById('chapterSize').value),
                mockMode: document.getElementById('mockMode').checked,
                debugMode: document.getElementById('debugMode').checked,
                keepParagraphComplete: document.getElementById('keepParagraphComplete').checked,
                darkTheme: document.body.classList.contains('dark-theme')
            };
            
            localStorage.setItem('novel-platform-settings', JSON.stringify(settings));
            this.state.set('settings', settings);
            
            // 重新初始化API
            this.initAPI();
            
            this.toastManager.success('设置已保存');
            console.log('[App] 设置已保存');
        } catch (error) {
            this.toastManager.error('保存设置失败');
            console.error('[App] 保存设置失败:', error);
        }
    }
    
    /**
     * 重置设置
     */
    resetSettings() {
        if (!confirm('确定要恢复默认设置吗？')) return;
        
        localStorage.removeItem('novel-platform-settings');
        
        // 恢复默认值
        document.getElementById('apiBaseUrl').value = 'http://localhost:8000/api/v1';
        document.getElementById('apiKey').value = '';
        document.getElementById('modelName').value = 'gpt-5.4-nano';
        document.getElementById('temperature').value = 0.7;
        document.getElementById('temperatureValue').textContent = '0.7';
        document.getElementById('maxTokens').value = 4096;
        document.getElementById('chapterSize').value = 2000;
        document.getElementById('mockMode').checked = true;
        document.getElementById('debugMode').checked = false;
        document.getElementById('keepParagraphComplete').checked = true;
        
        document.body.classList.remove('dark-theme');
        this.state.set('settings', {
            apiBaseUrl: 'http://localhost:8000/api/v1',
            apiKey: '',
            modelName: 'gpt-5.4-nano',
            temperature: 0.7,
            maxTokens: 4096,
            chapterSize: 2000,
            mockMode: true,
            debugMode: false,
            keepParagraphComplete: true,
            darkTheme: false
        });
        this.initAPI();
        
        this.toastManager.success('已恢复默认设置');
    }
}

// 创建全局应用实例
const app = new NovelPlatformApp();

// DOM加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    app.init();
});

// 导出供全局访问
window.app = app;

export { NovelPlatformApp };
