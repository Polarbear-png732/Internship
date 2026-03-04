/**
 * 扫描模块（scan）
 *
 * 职责：
 * - 扫描结果文件导入（上传、模式选择、执行、结果展示）
 * - 扫描统计加载
 * - 山东 md5 文本上传与回填触发
 *
 * 依赖关系：
 * - 依赖 common.js（API_BASE、showToast）
 */

// 扫描结果导入功能
// ============================================================

// 扫描导入状态
let scanImportState = {
    file: null,
    taskId: null,
    totalRows: 0
};

// 打开扫描结果导入模态框
function openScanImportModal() {
    document.getElementById('scan-import-modal').classList.remove('hidden');
    resetScanImportState();
    loadScanStats();
}

// 关闭扫描结果导入模态框
function closeScanImportModal() {
    document.getElementById('scan-import-modal').classList.add('hidden');
    resetScanImportState();
}

// 重置扫描导入状态
function resetScanImportState() {
    scanImportState = { file: null, taskId: null, totalRows: 0 };
    document.getElementById('scan-file-input').value = '';
    document.getElementById('scan-drop-zone').classList.remove('hidden');
    document.getElementById('scan-file-selected').classList.add('hidden');
    document.getElementById('scan-mode-selection').classList.add('hidden');
    document.getElementById('scan-import-result').classList.add('hidden');
    document.getElementById('scan-import-btn').disabled = true;
    document.getElementById('scan-import-btn').innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="17 8 12 3 7 8"/>
            <line x1="12" x2="12" y1="3" y2="15"/>
        </svg>
        开始导入
    `;
}

// 加载扫描结果统计
async function loadScanStats() {
    try {
        const response = await fetch(`${API_BASE}/scan-result/stats`);
        const result = await response.json();
        if (result.code === 200) {
            document.getElementById('scan-total-count').textContent = result.data.total.toLocaleString();
        }
    } catch (error) {
        console.error('加载扫描统计失败:', error);
        document.getElementById('scan-total-count').textContent = '-';
    }
}

// 拖拽处理
function handleScanDragOver(event) {
    event.preventDefault();
    event.currentTarget.classList.add('border-orange-400', 'bg-orange-50');
}

function handleScanDragLeave(event) {
    event.preventDefault();
    event.currentTarget.classList.remove('border-orange-400', 'bg-orange-50');
}

function handleScanDrop(event) {
    event.preventDefault();
    event.currentTarget.classList.remove('border-orange-400', 'bg-orange-50');
    
    const files = event.dataTransfer.files;
    if (files.length > 0) {
        handleScanFile(files[0]);
    }
}

// 文件选择处理
function handleScanFileSelect(event) {
    const files = event.target.files;
    if (files.length > 0) {
        handleScanFile(files[0]);
    }
}

// 处理选中的文件
function handleScanFile(file) {
    if (!file.name.toLowerCase().endsWith('.csv')) {
        showToast('请选择 CSV 文件', 'error');
        return;
    }
    
    scanImportState.file = file;
    
    // 显示文件信息
    document.getElementById('scan-drop-zone').classList.add('hidden');
    document.getElementById('scan-file-selected').classList.remove('hidden');
    document.getElementById('scan-mode-selection').classList.remove('hidden');
    document.getElementById('scan-file-name').textContent = file.name;
    document.getElementById('scan-file-info').textContent = `大小: ${(file.size / 1024 / 1024).toFixed(2)} MB`;
    document.getElementById('scan-import-btn').disabled = false;
}

// 清除选中的文件
function clearScanFile() {
    resetScanImportState();
}

function triggerShandongMd5Upload() {
    const fileInput = document.getElementById('shandong-md5-file-input');
    if (!fileInput) return;
    fileInput.value = '';
    fileInput.click();
}

async function handleShandongMd5FileSelect(event) {
    const file = event?.target?.files?.[0];
    if (!file) {
        return;
    }

    if (!file.name.toLowerCase().endsWith('.txt')) {
        showToast('请选择 .txt 文件', 'error');
        event.target.value = '';
        return;
    }

    const uploadBtn = document.getElementById('shandong-md5-btn');
    const originalHtml = uploadBtn ? uploadBtn.innerHTML : '';
    if (uploadBtn) {
        uploadBtn.disabled = true;
        uploadBtn.innerHTML = `
            <svg class="animate-spin" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10" stroke-opacity="0.25"/>
                <path d="M12 2a10 10 0 0 1 10 10" stroke-linecap="round"/>
            </svg>
            处理中...
        `;
    }

    try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${API_BASE}/scan-result/shandong-md5/upload`, {
            method: 'POST',
            body: formData
        });
        const result = await response.json();

        if (result.code !== 200) {
            throw new Error(result.detail || result.message || '山东MD5处理失败');
        }

        const data = result.data || {};
        showToast(
            `山东md5完成：解析${data.parsed_count || 0}，更新${data.updated_count || 0}，未命中${data.not_found_count || 0}，已有md5跳过${data.skipped_existing_count || 0}`,
            'success',
            5000
        );

        loadScanStats();
    } catch (error) {
        console.error('山东MD5处理失败:', error);
        showToast(error.message || '山东MD5处理失败', 'error');
    } finally {
        if (uploadBtn) {
            uploadBtn.disabled = false;
            uploadBtn.innerHTML = originalHtml;
        }
        event.target.value = '';
    }
}

// 执行扫描结果导入
async function executeScanImport() {
    if (!scanImportState.file) {
        showToast('请先选择文件', 'error');
        return;
    }
    
    const importBtn = document.getElementById('scan-import-btn');
    importBtn.disabled = true;
    importBtn.innerHTML = `
        <svg class="animate-spin" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10" stroke-opacity="0.25"/>
            <path d="M12 2a10 10 0 0 1 10 10" stroke-linecap="round"/>
        </svg>
        上传中...
    `;
    
    try {
        // 1. 上传文件
        const formData = new FormData();
        formData.append('file', scanImportState.file);
        
        const uploadResponse = await fetch(`${API_BASE}/scan-result/upload`, {
            method: 'POST',
            body: formData
        });
        const uploadResult = await uploadResponse.json();
        
        if (uploadResult.code !== 200) {
            throw new Error(uploadResult.detail || uploadResult.message || '上传失败');
        }
        
        scanImportState.taskId = uploadResult.data.task_id;
        scanImportState.totalRows = uploadResult.data.total_rows;
        
        // 更新文件信息
        document.getElementById('scan-file-info').textContent = `共 ${scanImportState.totalRows.toLocaleString()} 条记录`;
        
        // 2. 执行导入
        importBtn.innerHTML = `
            <svg class="animate-spin" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10" stroke-opacity="0.25"/>
                <path d="M12 2a10 10 0 0 1 10 10" stroke-linecap="round"/>
            </svg>
            导入中...
        `;
        
        const mode = document.querySelector('input[name="scan-import-mode"]:checked').value;
        
        const importResponse = await fetch(`${API_BASE}/scan-result/import/${scanImportState.taskId}?mode=${mode}`, {
            method: 'POST'
        });
        const importResult = await importResponse.json();
        
        if (importResult.code !== 200) {
            throw new Error(importResult.detail || importResult.message || '导入失败');
        }
        
        // 3. 显示结果
        document.getElementById('scan-import-result').classList.remove('hidden');
        document.getElementById('scan-result-total').textContent = importResult.data.total.toLocaleString();
        document.getElementById('scan-result-success').textContent = importResult.data.success_count.toLocaleString();
        document.getElementById('scan-result-skipped').textContent = importResult.data.skipped_count.toLocaleString();
        document.getElementById('scan-result-failed').textContent = importResult.data.failed_count.toLocaleString();
        
        // 刷新统计
        loadScanStats();
        
        showToast(`导入完成：成功 ${importResult.data.success_count} 条，跳过 ${importResult.data.skipped_count} 条`, 'success');
        
        importBtn.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="20 6 9 17 4 12"/>
            </svg>
            导入完成
        `;
        
    } catch (error) {
        console.error('导入失败:', error);
        showToast(error.message || '导入失败', 'error');
        importBtn.disabled = false;
        importBtn.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="17 8 12 3 7 8"/>
                <line x1="12" x2="12" y1="3" y2="15"/>
            </svg>
            重新导入
        `;
    }
}