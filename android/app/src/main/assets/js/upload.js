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

async function startProcessing() {
    if (!selectedFile) return;
    
    const formData = new FormData();
    formData.append('file', selectedFile);
    
    try {
        document.getElementById('startProcess').disabled = true;
        showToast('开始上传文件...', 'info');
        
        const response = await fetch(`${API_BASE}/api/books/upload`, {
            method: 'POST',
            body: formData
        });
        
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
