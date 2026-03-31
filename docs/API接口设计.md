# AI小说平台 - 拆书系统 API接口设计文档

## 文档信息
| 项目 | 内容 |
|------|------|
| 版本 | v1.0.0 |
| 创建日期 | 2024年 |
| 状态 | 初稿 |
| 基础路径 | /api/v1 |

---

## 一、接口概览

### 1.1 接口列表

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | /api/v1/books/upload | 上传书籍文件 | 可选 |
| GET | /api/v1/books | 获取书籍列表 | 可选 |
| GET | /api/v1/books/{bookId} | 获取书籍详情 | 可选 |
| DELETE | /api/v1/books/{bookId} | 删除书籍 | 可选 |
| GET | /api/v1/books/{bookId}/tree | 获取纲树结构 | 可选 |
| GET | /api/v1/books/{bookId}/status | 获取处理状态 | 可选 |
| GET | /api/v1/outlines/{outlineId} | 获取纲详情 | 可选 |
| POST | /api/v1/outlines/{outlineId}/copy | 复制纲内容 | 可选 |
| GET | /api/v1/tasks/{taskId} | 获取任务状态 | 可选 |
| GET | /api/v1/tasks/{taskId}/errors | 获取任务错误日志 | 可选 |
| WS | /api/v1/ws/{taskId} | 实时进度推送 | 可选 |

### 1.2 通用响应格式

\`\`\`json
{
  "success": true,
  "data": { ... },
  "error": null,
  "timestamp": "2024-01-15T10:30:45.123Z"
}
\`\`\`

### 1.3 错误响应格式

\`\`\`json
{
  "success": false,
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述信息",
    "details": { ... }
  },
  "timestamp": "2024-01-15T10:30:45.123Z"
}
\`\`\`

### 1.4 错误码定义

| 错误码 | HTTP状态码 | 说明 |
|--------|-----------|------|
| INVALID_FILE_FORMAT | 400 | 不支持的文件格式 |
| FILE_TOO_LARGE | 413 | 文件超过大小限制 |
| ENCODING_DETECTION_FAILED | 400 | 无法检测文本编码 |
| BOOK_NOT_FOUND | 404 | 书籍不存在 |
| OUTLINE_NOT_FOUND | 404 | 纲不存在 |
| TASK_NOT_FOUND | 404 | 任务不存在 |
| PROCESSING_FAILED | 500 | 处理过程失败 |
| LLM_ERROR | 502 | LLM调用失败 |
| INTERNAL_ERROR | 500 | 内部服务器错误 |

---

## 二、书籍相关接口

### 2.1 上传书籍文件

**POST** \`/api/v1/books/upload\`

**请求：**
- Content-Type: \`multipart/form-data\`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | File | 是 | 书籍文件 (epub/txt/doc/docx/pdf) |
| title | String | 否 | 书名（默认从文件名提取） |
| author | String | 否 | 作者 |

**响应示例：**
\`\`\`json
{
  "success": true,
  "data": {
    "bookId": "book_550e8400-e29b-41d4-a716-446655440000",
    "taskId": "task_550e8400-e29b-41d4-a716-446655440001",
    "fileName": "novel.txt",
    "fileSize": 1024000,
    "status": "UPLOADING",
    "message": "文件上传成功，正在开始处理..."
  },
  "timestamp": "2024-01-15T10:30:45.123Z"
}
\`\`\`

---

### 2.2 获取书籍列表

**GET** \`/api/v1/books\`

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | String | 否 | 按状态筛选 (IDLE/PROCESSING/COMPLETED/ERROR) |
| page | Integer | 否 | 页码，默认1 |
| pageSize | Integer | 否 | 每页数量，默认20，最大100 |
| sortBy | String | 否 | 排序字段 (createdAt/title/status) |
| sortOrder | String | 否 | 排序方向 (asc/desc)，默认desc |

**响应示例：**
\`\`\`json
{
  "success": true,
  "data": {
    "books": [
      {
        "bookId": "book_550e8400-e29b-41d4-a716-446655440000",
        "title": "我的小说",
        "originalName": "novel.txt",
        "fileType": "TXT",
        "fileSize": 1024000,
        "totalChapters": 100,
        "status": "COMPLETED",
        "createdAt": "2024-01-15T10:30:45.123Z",
        "updatedAt": "2024-01-15T12:30:45.123Z"
      }
    ],
    "pagination": {
      "page": 1,
      "pageSize": 20,
      "total": 1,
      "totalPages": 1
    }
  },
  "timestamp": "2024-01-15T10:30:45.123Z"
}
\`\`\`

---

### 2.3 获取书籍详情

**GET** \`/api/v1/books/{bookId}\`

**路径参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| bookId | String | 是 | 书籍ID |

**响应示例：**
\`\`\`json
{
  "success": true,
  "data": {
    "bookId": "book_550e8400-e29b-41d4-a716-446655440000",
    "title": "我的小说",
    "originalName": "novel.txt",
    "fileType": "TXT",
    "fileSize": 1024000,
    "encoding": "UTF-8",
    "totalChapters": 100,
    "status": "COMPLETED",
    "createdAt": "2024-01-15T10:30:45.123Z",
    "updatedAt": "2024-01-15T12:30:45.123Z"
  },
  "timestamp": "2024-01-15T10:30:45.123Z"
}
\`\`\`

---

### 2.4 删除书籍

**DELETE** \`/api/v1/books/{bookId}\`

**响应示例：**
\`\`\`json
{
  "success": true,
  "data": {
    "bookId": "book_550e8400-e29b-41d4-a716-446655440000",
    "message": "书籍已删除"
  },
  "timestamp": "2024-01-15T10:30:45.123Z"
}
\`\`\`

---

## 三、纲相关接口

### 3.1 获取纲树结构

**GET** \`/api/v1/books/{bookId}/tree\`

**说明：** 返回指定书籍的完整纲层级树结构，用于前端树形图展示。

**响应示例：**
\`\`\`json
{
  "success": true,
  "data": {
    "bookId": "book_550e8400-e29b-41d4-a716-446655440000",
    "tree": {
      "outlineId": "outline_world_001",
      "outlineType": "WORLD",
      "label": "世界纲",
      "summary": "这是一个宏大的修仙世界...",
      "status": "COMPLETED",
      "childCount": 3,
      "children": [
        {
          "outlineId": "outline_main_001",
          "outlineType": "MAIN",
          "outlineIndex": 1,
          "label": "大纲 1 (章节1-100)",
          "summary": "第一部分讲述了主角的觉醒与初步成长...",
          "status": "COMPLETED",
          "chapterRange": [1, 100],
          "childCount": 10,
          "children": []
        }
      ]
    }
  },
  "timestamp": "2024-01-15T10:30:45.123Z"
}
\`\`\`

---

### 3.2 获取纲详情

**GET** \`/api/v1/outlines/{outlineId}\`

**说明：** 获取单个纲的完整内容详情。

**响应示例（章纲）：**
\`\`\`json
{
  "success": true,
  "data": {
    "outlineId": "outline_chapter_001",
    "bookId": "book_550e8400-e29b-41d4-a716-446655440000",
    "outlineType": "CHAPTER",
    "chapterIndex": 1,
    "status": "COMPLETED",
    "content": {
      "generalStyle": "本章节采用第三人称视角叙述...",
      "globalVisualRhythm": "节奏先缓后急...",
      "settingsTemplate": {
        "characters": ["主角：林风", "配角：村长李伯"],
        "locations": ["青石村", "后山"],
        "items": ["祖传玉佩"]
      },
      "plotStyleIntegration": {
        "plotElements": {
          "mainPlot": "主角林风在村中过着平凡生活",
          "conflict": "突然出现的神秘人打破平静",
          "climax": "玉佩觉醒，主角获得神秘力量"
        },
        "styleAnalysis": "文风质朴中带有神秘感..."
      },
      "summary": "本章主要介绍主角林风的背景..."
    },
    "summary": "本章主要介绍主角林风的背景...",
    "createdAt": "2024-01-15T11:00:00.000Z"
  },
  "timestamp": "2024-01-15T10:30:45.123Z"
}
\`\`\`

---

### 3.3 复制纲内容

**POST** \`/api/v1/outlines/{outlineId}/copy\`

**响应示例：**
\`\`\`json
{
  "success": true,
  "data": {
    "outlineId": "outline_chapter_001",
    "outlineType": "CHAPTER",
    "copyContent": "【章纲 1】\n\n概括：本章主要介绍主角林风的背景...",
    "copyFormat": "text"
  },
  "timestamp": "2024-01-15T10:30:45.123Z"
}
\`\`\`

---

## 四、任务相关接口

### 4.1 获取任务状态

**GET** \`/api/v1/tasks/{taskId}\`

**响应示例：**
\`\`\`json
{
  "success": true,
  "data": {
    "taskId": "task_550e8400-e29b-41d4-a716-446655440001",
    "bookId": "book_550e8400-e29b-41d4-a716-446655440000",
    "status": "RUNNING",
    "currentStage": "CHAPTER_OUTLINE",
    "stageProgress": {
      "FILE_UPLOAD": 100,
      "TEXT_PREPROCESS": 100,
      "CHAPTER_OUTLINE": 45,
      "COARSE_OUTLINE": 0,
      "MAIN_OUTLINE": 0,
      "WORLD_OUTLINE": 0
    },
    "totalChapters": 100,
    "completedChapters": 45,
    "errorCount": 0,
    "startTime": "2024-01-15T10:30:00.000Z",
    "endTime": null,
    "estimatedTimeRemaining": 1800
  },
  "timestamp": "2024-01-15T10:45:00.000Z"
}
\`\`\`

---

### 4.2 获取任务错误日志

**GET** \`/api/v1/tasks/{taskId}/errors\`

**响应示例：**
\`\`\`json
{
  "success": true,
  "data": {
    "taskId": "task_550e8400-e29b-41d4-a716-446655440001",
    "totalErrors": 2,
    "errors": [
      {
        "errorId": "error_001",
        "stage": "CHAPTER_OUTLINE",
        "chapterIndex": 23,
        "errorType": "LLM_TIMEOUT",
        "errorMessage": "LLM调用超时，将在30秒后重试",
        "timestamp": "2024-01-15T11:00:00.000Z"
      }
    ]
  },
  "timestamp": "2024-01-15T12:00:00.000Z"
}
\`\`\`

---

## 五、WebSocket接口

### 5.1 实时进度推送

**WebSocket** \`/api/v1/ws/{taskId}\`

**消息类型：**

#### 进度更新消息
\`\`\`json
{
  "type": "progress",
  "payload": {
    "taskId": "task_xxx",
    "stage": "CHAPTER_OUTLINE",
    "progress": 45,
    "total": 100,
    "completed": 45,
    "message": "正在提取第45章章纲..."
  },
  "timestamp": "2024-01-15T10:45:00.000Z"
}
\`\`\`

#### 纲更新消息
\`\`\`json
{
  "type": "outline_update",
  "payload": {
    "outlineId": "outline_chapter_045",
    "outlineType": "CHAPTER",
    "chapterIndex": 45,
    "status": "COMPLETED",
    "summary": "第45章讲述了..."
  },
  "timestamp": "2024-01-15T10:45:30.000Z"
}
\`\`\`

#### 错误消息
\`\`\`json
{
  "type": "error",
  "payload": {
    "taskId": "task_xxx",
    "stage": "CHAPTER_OUTLINE",
    "chapterIndex": 23,
    "errorType": "LLM_TIMEOUT",
    "errorMessage": "LLM调用超时",
    "willRetry": true,
    "retryAfter": 30
  },
  "timestamp": "2024-01-15T10:45:00.000Z"
}
\`\`\`

#### 完成消息
\`\`\`json
{
  "type": "completed",
  "payload": {
    "taskId": "task_xxx",
    "bookId": "book_xxx",
    "status": "COMPLETED",
    "totalChapters": 100,
    "totalTime": 7200,
    "worldOutlineId": "outline_world_001"
  },
  "timestamp": "2024-01-15T12:30:00.000Z"
}
\`\`\`

---

## 六、版本记录

| 版本 | 日期 | 修改内容 |
|------|------|---------|
| v1.0.0 | 2024-01-15 | 初始版本 |
