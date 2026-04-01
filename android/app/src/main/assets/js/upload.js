let selectedFile = null;

document.addEventListener('DOMContentLoaded', () => {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');
    const fileInfo = document.getElementById('fileInfo');
    const startBtn = document.getElementById('startProcess');
    
    uploadArea.addEventListener('click', () => fileInput.click());
    
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            handleFileSelect(e.dataTransfer.files[0]);
        }
    });
    
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileSelect(e.target.files[0]);
        }
    });
    
    startBtn.addEventListener('click', startProcessing);
});

function handleFileSelect(file) {
    const validExts = ['epub', 'txt', 'doc', 'docx', 'pdf'];
    const ext = file.name.split('.').pop().toLowerCase();
    
    if (!validExts.includes(ext)) {
        showToast('不支持的文件格式', 'error');
        return;
    }
    
    selectedFile = file;
    const fileInfo = document.getElementById('fileInfo');
    fileInfo.innerHTML = `
        <div>
            <div class="file-name">${file.name}</div>
            <div class="file-size">${(file.size / 1024 / 1024).toFixed(2)} MB</div>
        </div>
    `;
    fileInfo.classList.remove('hidden');
    document.getElementById('startProcess').classList.remove('hidden');
}

async function startProcessing(forceUpload = false) {
    if (!selectedFile) return;
    
    const formData = new FormData();
    formData.append('file', selectedFile);
    if (forceUpload) {
        formData.append('force', 'true');
    }
    
    try {
        document.getElementById('startProcess').disabled = true;
        showToast('开始上传文件...', 'info');
        
        const response = await fetch(`${API_BASE}/api/books/upload`, {
            method: 'POST',
            body: formData
        });
        
        if (response.status === 409) {
            const errorData = await response.json();
            const details = errorData.detail?.details || {};
            const existingTitle = details.existingTitle || '未知书籍';
            const existingName = details.existingOriginalName || '';
            const statusMap = { IDLE: '空闲', PROCESSING: '处理中', COMPLETED: '已完成', ERROR: '错误' };
            const existingStatus = statusMap[details.existingStatus] || details.existingStatus || '';
            
            document.getElementById('startProcess').disabled = false;
            
            const confirmed = await showDuplicateConfirm(existingTitle, existingName, existingStatus);
            if (confirmed) {
                return startProcessing(true);
            }
            return;
        }
        
        if (!response.ok) throw new Error('上传失败');
        
        const result = await response.json();
        showToast('上传成功，开始处理', 'success');
        
        setTimeout(() => {
            document.querySelector('[data-page="monitor"]').click();
        }, 1000);
    } catch (error) {
        showToast('上传失败: ' + error.message, 'error');
        document.getElementById('startProcess').disabled = false;
    }
}

function showDuplicateConfirm(title, originalName, status) {
    return new Promise((resolve) => {
        const overlay = document.createElement('div');
        overlay.id = 'duplicateConfirmOverlay';
        overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.6);z-index:10000;display:flex;align-items:center;justify-content:center;';
        
        const dialog = document.createElement('div');
        dialog.style.cssText = 'background:var(--bg-secondary,#1e1e2e);border:1px solid var(--border-color,#333);border-radius:12px;padding:28px 32px;max-width:420px;width:90%;box-shadow:0 8px 32px rgba(0,0,0,0.4);';
        
        const iconDiv = document.createElement('div');
        iconDiv.style.cssText = 'text-align:center;margin-bottom:16px;';
        iconDiv.innerHTML = '<svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>';
        
        const titleEl = document.createElement('h3');
        titleEl.textContent = '检测到重复书籍';
        titleEl.style.cssText = 'text-align:center;color:var(--text-primary,#e0e0e0);margin:0 0 16px 0;font-size:18px;';
        
        const info = document.createElement('div');
        info.style.cssText = 'background:var(--bg-primary,#16161e);border-radius:8px;padding:14px 16px;margin-bottom:20px;font-size:14px;color:var(--text-secondary,#aaa);line-height:1.8;';
        info.innerHTML = `已存在相同内容的书籍：<br><strong style="color:var(--text-primary,#e0e0e0);">${title}</strong>${originalName ? ` (${originalName})` : ''}<br>状态：${status}`;
        
        const btnContainer = document.createElement('div');
        btnContainer.style.cssText = 'display:flex;gap:12px;justify-content:flex-end;';
        
        const cancelBtn = document.createElement('button');
        cancelBtn.textContent = '取消上传';
        cancelBtn.style.cssText = 'padding:8px 20px;border-radius:8px;border:1px solid var(--border-color,#444);background:transparent;color:var(--text-secondary,#aaa);cursor:pointer;font-size:14px;transition:all 0.2s;';
        cancelBtn.onmouseover = () => cancelBtn.style.background = 'var(--bg-hover,#2a2a3a)';
        cancelBtn.onmouseout = () => cancelBtn.style.background = 'transparent';
        cancelBtn.onclick = () => {
            document.body.removeChild(overlay);
            resolve(false);
        };
        
        const confirmBtn = document.createElement('button');
        confirmBtn.textContent = '仍然继续';
        confirmBtn.style.cssText = 'padding:8px 20px;border-radius:8px;border:none;background:var(--accent,#6366f1);color:#fff;cursor:pointer;font-size:14px;font-weight:500;transition:all 0.2s;';
        confirmBtn.onmouseover = () => confirmBtn.style.opacity = '0.85';
        confirmBtn.onmouseout = () => confirmBtn.style.opacity = '1';
        confirmBtn.onclick = () => {
            document.body.removeChild(overlay);
            resolve(true);
        };
        
        btnContainer.appendChild(cancelBtn);
        btnContainer.appendChild(confirmBtn);
        dialog.appendChild(iconDiv);
        dialog.appendChild(titleEl);
        dialog.appendChild(info);
        dialog.appendChild(btnContainer);
        overlay.appendChild(dialog);
        document.body.appendChild(overlay);
    });
}
