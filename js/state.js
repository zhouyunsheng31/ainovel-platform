/**
 * AI小说拆书系统 - 状态管理模块
 * 集中管理应用状态
 */

class StateManager {
  // 单例实例
  static #instance = null;
  
  constructor() {
    if (StateManager.#instance) {
      return StateManager.#instance;
    }
    
    this.state = {
      // 当前激活页面
      currentPage: 'upload',
      
      // 书籍列表
      books: [],
      
      // 当前选中的书籍ID
      selectedBookId: null,
      
      // 当前处理的任务
      currentTask: null,
      
      // 处理进度
      processingStatus: {
        fileUpload: { status: 'pending', progress: 0 },
        textPreprocess: { status: 'pending', progress: 0 },
        chapterOutline: { status: 'pending', progress: 0, total: 0, completed: 0 },
        coarseOutline: { status: 'pending', progress: 0, total: 0, completed: 0 },
        mainOutline: { status: 'pending', progress: 0, total: 0, completed: 0 },
        worldOutline: { status: 'pending', progress: 0 }
      },
      
      // 错误列表
      errors: [],
      
      // 纲树数据
      outlineTree: null,
      
      // 当前选中节点
      selectedNode: null,
      
      // WebSocket连接状态
      wsConnected: false,
      
      // 设置
      settings: {}
    };
    
    this.listeners = new Map();
    this.nextListenerId = 1;
    
    // 保存单例实例
    StateManager.#instance = this;
  }
  
  /**
   * 获取单例实例
   */
  static getInstance() {
    if (!StateManager.#instance) {
      new StateManager();
    }
    return StateManager.#instance;
  }
  
  /**
   * 获取状态
   */
  getState(path) {
    if (!path) return { ...this.state };
    
    const keys = path.split('.');
    let value = this.state;
    
    for (const key of keys) {
      if (value === undefined || value === null) return undefined;
      value = value[key];
    }
    
    return value;
  }
  
  /**
   * 设置状态
   */
  setState(path, value) {
    const keys = path.split('.');
    const lastKey = keys.pop();
    let target = this.state;
    
    for (const key of keys) {
      if (!(key in target)) {
        target[key] = {};
      }
      target = target[key];
    }
    
    target[lastKey] = value;
    this.notify(path);
  }
  
  /**
   * 获取状态（简写别名）
   */
  get(path) {
    return this.getState(path);
  }
  
  /**
   * 设置状态（简写别名）
   */
  set(path, value) {
    return this.setState(path, value);
  }
  
  /**
   * 删除状态
   */
  delete(path) {
    const keys = path.split('.');
    const lastKey = keys.pop();
    let target = this.state;
    
    for (const key of keys) {
      if (!(key in target)) {
        return false;
      }
      target = target[key];
    }
    
    if (target && lastKey in target) {
      delete target[lastKey];
      this.notify(path);
      return true;
    }
    return false;
  }
  
  /**
   * 批量更新状态
   */
  batchUpdate(updates) {
    const paths = [];
    for (const [path, value] of Object.entries(updates)) {
      const keys = path.split('.');
      const lastKey = keys.pop();
      let target = this.state;
      
      for (const key of keys) {
        if (!(key in target)) {
          target[key] = {};
        }
        target = target[key];
      }
      
      target[lastKey] = value;
      paths.push(path);
    }
    
    paths.forEach(path => this.notify(path));
  }
  
  /**
   * 订阅状态变化
   * @returns {number} 订阅ID，用于取消订阅
   */
  subscribe(path, callback) {
    const id = this.nextListenerId++;
    
    if (!this.listeners.has(path)) {
      this.listeners.set(path, new Map());
    }
    
    this.listeners.get(path).set(id, callback);
    return id;
  }
  
  /**
   * 取消订阅
   */
  unsubscribe(path, id) {
    if (this.listeners.has(path)) {
      this.listeners.get(path).delete(id);
    }
  }
  
  /**
   * 通知订阅者
   */
  notify(path) {
    if (this.listeners.has(path)) {
      const value = this.getState(path);
      this.listeners.get(path).forEach(callback => {
        try {
          callback(value);
        } catch (e) {
          console.error('State listener error:', e);
        }
      });
    }
  }
  
  /**
   * 重置状态
   */
  reset() {
    this.state = {
      currentPage: 'upload',
      books: [],
      selectedBookId: null,
      currentTask: null,
      processingStatus: {
        fileUpload: { status: 'pending', progress: 0 },
        textPreprocess: { status: 'pending', progress: 0 },
        chapterOutline: { status: 'pending', progress: 0, total: 0, completed: 0 },
        coarseOutline: { status: 'pending', progress: 0, total: 0, completed: 0 },
        mainOutline: { status: 'pending', progress: 0, total: 0, completed: 0 },
        worldOutline: { status: 'pending', progress: 0 }
      },
      errors: [],
      outlineTree: null,
      selectedNode: null,
      wsConnected: false
    };
    
    this.listeners.forEach((_, path) => this.notify(path));
  }
}

// 导出单例和类
const stateManager = new StateManager();
export default stateManager;
export { StateManager };
