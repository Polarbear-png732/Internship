/**
 * 版权模块（copyright）
 *
 * 职责：
 * - 版权列表查询、分页、搜索、增删改
 * - 版权导入（模板下载、上传、解析、执行、进度轮询）
 * - 版权相关弹窗渲染与表单提交
 *
 * 依赖关系：
 * - 依赖 common.js 提供的全局状态、showToast/showError、页面工具函数
 * - 由 index.html 在 common.js 后加载
 */

// ==================== 版权方数据管理 ====================

let copyrightCurrentPage = 1;
let backfillTaskState = {
    taskId: null,
    pollTimer: null
};

// 加载版权方数据列表
async function loadCopyrightList(page = 1) {
    copyrightCurrentPage = page;
    const keyword = document.getElementById('copyright-search-input')?.value?.trim() || '';
    
    try {
        let url = `${API_BASE}/copyright?page=${page}&page_size=${pageSize}`;
        if (keyword) {
            url += `&keyword=${encodeURIComponent(keyword)}`;
        }
        
        const response = await fetch(url);
        const result = await response.json();
        
        if (result.code === 200) {
            renderCopyrightTable(result.data.list);
            renderCopyrightPagination(result.data);
        } else {
            showError('加载数据失败：' + result.message);
        }
    } catch (error) {
        showError('加载数据失败：' + error.message);
    }
}

// 搜索版权方数据
function searchCopyrightContent() {
    loadCopyrightList(1);
}

// 导出版权方数据
function exportCopyrightData() {
    window.location.href = '/api/copyright/export';
}

// 渲染版权方数据表格
function renderCopyrightTable(items) {
    const tbody = document.getElementById('copyright-table-body');
    
    if (!items || items.length === 0) {
        tbody.innerHTML = '<tr><td colspan="34" class="px-6 py-12 text-center text-slate-500"><div class="flex flex-col items-center gap-3"><svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="text-slate-300"><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/></svg><span class="text-base">暂无版权方数据</span></div></td></tr>';
        return;
    }
    
    tbody.innerHTML = items.map((item, index) => {
        const rowClass = index % 2 === 0 ? 'bg-white' : 'bg-slate-50/30';
        const truncate = (text, len = 20) => {
            if (!text) return '-';
            return text.length > len ? text.substring(0, len) + '...' : text;
        };
        return `
            <tr class="${rowClass} hover:bg-blue-50/50 transition-all duration-200 border-b border-slate-100 group">
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${item.serial_number || item.id || '-'}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${truncate(item.upstream_copyright, 15)}</td>
                <td class="px-4 py-3 text-sm font-medium text-slate-900 whitespace-nowrap">${truncate(item.media_name, 20)}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${item.category_level1 || '-'}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${item.category_level2 || '-'}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${item.category_level1_henan || '-'}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${item.category_level2_henan || '-'}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${item.episode_count || '-'}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${item.single_episode_duration || '-'}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${item.total_duration || '-'}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${item.production_year || '-'}</td>
                <td class="px-4 py-3 text-sm text-green-700 font-medium whitespace-nowrap bg-green-50/50">${item.premiere_date || '-'}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${truncate(item.authorization_region, 10)}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${truncate(item.authorization_platform, 15)}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${truncate(item.cooperation_mode, 10)}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${truncate(item.production_region, 10)}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${item.language || '-'}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${item.language_henan || '-'}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${item.country || '-'}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${truncate(item.director, 15)}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${truncate(item.screenwriter, 15)}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${truncate(item.cast_members, 20)}</td>
                <td class="px-4 py-3 text-sm text-green-700 font-medium whitespace-nowrap bg-green-50/50">${truncate(item.author, 15)}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${truncate(item.recommendation, 15)}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${truncate(item.synopsis, 20)}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${truncate(item.keywords, 15)}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${item.video_quality || '-'}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${truncate(item.license_number, 15)}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${item.rating || '-'}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${item.exclusive_status || '-'}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${item.copyright_start_date || '-'}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${item.copyright_end_date || '-'}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${item.category_level2_shandong || '-'}</td>
                <td class="px-4 py-3 text-right whitespace-nowrap sticky right-0 ${rowClass} group-hover:bg-blue-50/50">
                    <div class="flex items-center justify-end gap-2">
                        <button onclick="editCopyrightContent(${item.id})" 
                            class="text-blue-600 hover:text-blue-700 font-medium text-sm inline-flex items-center gap-1 bg-blue-50 hover:bg-blue-100 border border-blue-200 px-2 py-1 rounded-lg transition-all">
                            编辑
                        </button>
                        <button onclick="deleteCopyrightContent(${item.id}, '${(item.media_name || '').replace(/'/g, "\\'")}')" 
                            class="text-red-600 hover:text-red-700 font-medium text-sm inline-flex items-center gap-1 bg-red-50 hover:bg-red-100 border border-red-200 px-2 py-1 rounded-lg transition-all">
                            删除
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

// 渲染版权方数据分页
function renderCopyrightPagination(data) {
    const pagination = document.getElementById('copyright-pagination');
    const totalPages = data.total_pages;
    
    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }
    
    pagination.innerHTML = `
        <button ${copyrightCurrentPage === 1 ? 'disabled' : ''} 
            onclick="loadCopyrightList(${copyrightCurrentPage - 1})"
            class="px-4 py-2 border border-slate-300 rounded-lg bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
            上一页
        </button>
        <span class="text-sm text-slate-600 mx-4">第 ${copyrightCurrentPage} / ${totalPages} 页，共 ${data.total} 条</span>
        <button ${copyrightCurrentPage === totalPages ? 'disabled' : ''} 
            onclick="loadCopyrightList(${copyrightCurrentPage + 1})"
            class="px-4 py-2 border border-slate-300 rounded-lg bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
            下一页
        </button>
    `;
}

// 打开添加版权方数据模态框
async function openAddCopyrightModal() {
    document.getElementById('copyright-modal-title').innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-blue-600">
            <line x1="12" x2="12" y1="5" y2="19"/>
            <line x1="5" x2="19" y1="12" y2="12"/>
        </svg>
        添加版权数据
    `;
    document.getElementById('copyright-edit-id').value = '';
    document.getElementById('add-copyright-form').reset();
    
    document.getElementById('add-copyright-modal').classList.remove('hidden');
}

// 关闭添加版权方数据模态框
function closeAddCopyrightModal() {
    document.getElementById('add-copyright-modal').classList.add('hidden');
    // 清空edit-id，防止下次打开时误用
    document.getElementById('copyright-edit-id').value = '';
    document.getElementById('add-copyright-form').reset();
}

// 编辑版权方数据
async function editCopyrightContent(id) {
    try {
        const response = await fetch(`${API_BASE}/copyright/${id}`);
        const result = await response.json();
        
        if (result.code === 200) {
            const item = result.data;
            
            document.getElementById('copyright-modal-title').innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-blue-600">
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                </svg>
                编辑版权数据
            `;
            
            document.getElementById('copyright-edit-id').value = id;
            
            // 基本信息
            document.getElementById('copyright-media-name').value = item.media_name || '';
            document.getElementById('copyright-upstream').value = item.upstream_copyright || '';
            document.getElementById('copyright-episode-count').value = item.episode_count || '';
            document.getElementById('copyright-single-duration').value = item.single_episode_duration || '';
            document.getElementById('copyright-total-duration').value = item.total_duration || '';
            document.getElementById('copyright-production-year').value = item.production_year || '';
            document.getElementById('copyright-premiere-date').value = item.premiere_date || '';
            document.getElementById('copyright-production-region').value = item.production_region || '';
            document.getElementById('copyright-country').value = item.country || '';
            document.getElementById('copyright-language').value = item.language || '';
            document.getElementById('copyright-language-henan').value = item.language_henan || '';
            document.getElementById('copyright-video-quality').value = item.video_quality || '';
            
            // 分类信息
            document.getElementById('copyright-category1').value = item.category_level1 || '';
            document.getElementById('copyright-category2').value = item.category_level2 || '';
            document.getElementById('copyright-category1-henan').value = item.category_level1_henan || '';
            document.getElementById('copyright-category2-henan').value = item.category_level2_henan || '';
            document.getElementById('copyright-category2-shandong').value = item.category_level2_shandong || '';
            
            // 版权信息
            document.getElementById('copyright-authorization-region').value = item.authorization_region || '';
            document.getElementById('copyright-authorization-platform').value = item.authorization_platform || '';
            document.getElementById('copyright-cooperation-mode').value = item.cooperation_mode || '';
            document.getElementById('copyright-start-date').value = item.copyright_start_date || '';
            document.getElementById('copyright-end-date').value = item.copyright_end_date || '';
            document.getElementById('copyright-license-number').value = item.license_number || '';
            document.getElementById('copyright-exclusive').value = item.exclusive_status || '';
            document.getElementById('copyright-rating').value = item.rating || '';
            
            // 主创信息
            document.getElementById('copyright-director').value = item.director || '';
            document.getElementById('copyright-screenwriter').value = item.screenwriter || '';
            document.getElementById('copyright-author').value = item.author || '';
            document.getElementById('copyright-cast').value = item.cast_members || '';
            
            // 描述信息
            document.getElementById('copyright-keywords').value = item.keywords || '';
            document.getElementById('copyright-recommendation').value = item.recommendation || '';
            document.getElementById('copyright-synopsis').value = item.synopsis || '';
            
            document.getElementById('add-copyright-modal').classList.remove('hidden');
        } else {
            showError('获取数据失败：' + result.message);
        }
    } catch (error) {
        showError('获取数据失败：' + error.message);
    }
}

// 保存版权方数据
async function saveCopyrightContent() {
    const editId = document.getElementById('copyright-edit-id').value;
    const mediaName = document.getElementById('copyright-media-name').value.trim();
    const episodeCountRaw = document.getElementById('copyright-episode-count').value.trim();
    const isCreateMode = !(editId && editId.trim() !== '');
    
    console.log('saveCopyrightContent - editId:', editId, 'type:', typeof editId);
    
    if (!mediaName) {
        showError('介质名称不能为空');
        return;
    }

    if (isCreateMode && !episodeCountRaw) {
        showError('集数为必填项');
        document.getElementById('copyright-episode-count').focus();
        return;
    }

    let episodeCount = null;
    if (episodeCountRaw) {
        episodeCount = parseInt(episodeCountRaw, 10);
        if (!Number.isInteger(episodeCount) || episodeCount <= 0) {
            showError('集数必须是大于 0 的整数');
            document.getElementById('copyright-episode-count').focus();
            return;
        }
    }
    
    const data = {
        // 基本信息
        media_name: mediaName,
        upstream_copyright: document.getElementById('copyright-upstream').value.trim() || null,
        episode_count: episodeCount,
        single_episode_duration: parseFloat(document.getElementById('copyright-single-duration').value) || null,
        total_duration: parseFloat(document.getElementById('copyright-total-duration').value) || null,
        production_year: parseInt(document.getElementById('copyright-production-year').value) || null,
        premiere_date: document.getElementById('copyright-premiere-date').value.trim() || null,
        production_region: document.getElementById('copyright-production-region').value.trim() || null,
        country: document.getElementById('copyright-country').value.trim() || null,
        language: document.getElementById('copyright-language').value.trim() || null,
        language_henan: document.getElementById('copyright-language-henan').value.trim() || null,
        video_quality: document.getElementById('copyright-video-quality').value.trim() || null,
        
        // 分类信息
        category_level1: document.getElementById('copyright-category1').value.trim() || null,
        category_level2: document.getElementById('copyright-category2').value.trim() || null,
        category_level1_henan: document.getElementById('copyright-category1-henan').value.trim() || null,
        category_level2_henan: document.getElementById('copyright-category2-henan').value.trim() || null,
        category_level2_shandong: document.getElementById('copyright-category2-shandong').value.trim() || null,
        
        // 版权信息
        authorization_region: document.getElementById('copyright-authorization-region').value.trim() || null,
        authorization_platform: document.getElementById('copyright-authorization-platform').value.trim() || null,
        cooperation_mode: document.getElementById('copyright-cooperation-mode').value.trim() || null,
        copyright_start_date: document.getElementById('copyright-start-date').value.trim() || null,
        copyright_end_date: document.getElementById('copyright-end-date').value.trim() || null,
        license_number: document.getElementById('copyright-license-number').value.trim() || null,
        exclusive_status: document.getElementById('copyright-exclusive').value.trim() || null,
        rating: parseFloat(document.getElementById('copyright-rating').value) || null,
        
        // 主创信息
        director: document.getElementById('copyright-director').value.trim() || null,
        screenwriter: document.getElementById('copyright-screenwriter').value.trim() || null,
        author: document.getElementById('copyright-author').value.trim() || null,
        cast_members: document.getElementById('copyright-cast').value.trim() || null,
        
        // 描述信息
        keywords: document.getElementById('copyright-keywords').value.trim() || null,
        recommendation: document.getElementById('copyright-recommendation').value.trim() || null,
        synopsis: document.getElementById('copyright-synopsis').value.trim() || null
    };
    
    try {
        let url = `${API_BASE}/copyright`;
        let method = 'POST';
        
        // 更严格的判断：editId存在且不为空字符串
        if (editId && editId.trim() !== '') {
            url = `${API_BASE}/copyright/${editId}`;
            method = 'PUT';
            console.log('执行更新操作，URL:', url);
        } else {
            console.log('执行新增操作，URL:', url);
        }
        
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.code === 200) {
            showSuccess(editId ? '更新成功！' : '添加成功！自动创建了剧头和子集数据');
            closeAddCopyrightModal();
            loadCopyrightList(copyrightCurrentPage);
        } else {
            showError(result.message || '保存失败');
        }
    } catch (error) {
        showError('保存失败：' + error.message);
    }
}

// 删除版权方数据
async function deleteCopyrightContent(id, mediaName) {
    if (!confirm(`确定要删除"${mediaName}"吗？此操作不可撤销！`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/copyright/${id}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.code === 200) {
            showSuccess('删除成功！');
            loadCopyrightList(copyrightCurrentPage);
        } else {
            showError(result.message || '删除失败');
        }
    } catch (error) {
        showError('删除失败：' + error.message);
    }
}


// ==================== 子集管理功能 ====================

let currentEditEpisodeId = null;

// 打开添加子集模态框
function openAddEpisodeModal() {
    if (!currentDramaId) {
        showError('请先选择一个剧集');
        return;
    }
    
    // 清空表单
    document.getElementById('episode-name').value = '';
    document.getElementById('episode-media-url').value = '';
    document.getElementById('episode-media-type').value = '';
    document.getElementById('episode-encoding').value = '';
    document.getElementById('episode-number').value = '';
    document.getElementById('episode-duration').value = '';
    document.getElementById('episode-file-size').value = '';
    
    currentEditEpisodeId = null;
    document.getElementById('episode-modal-title').textContent = '添加子集';
    document.getElementById('episode-modal').classList.remove('hidden');
}

// 打开编辑子集模态框
function openEditEpisodeModal(episodeId, name, mediaUrl, mediaType, encoding, episodeNum, duration, fileSize) {
    currentEditEpisodeId = episodeId;
    
    document.getElementById('episode-name').value = name || '';
    document.getElementById('episode-media-url').value = mediaUrl || '';
    document.getElementById('episode-media-type').value = mediaType || '';
    document.getElementById('episode-encoding').value = encoding || '';
    document.getElementById('episode-number').value = episodeNum || '';
    document.getElementById('episode-duration').value = duration || '';
    document.getElementById('episode-file-size').value = fileSize || '';
    
    document.getElementById('episode-modal-title').textContent = '编辑子集';
    document.getElementById('episode-modal').classList.remove('hidden');
}

// 关闭子集模态框
function closeEpisodeModal() {
    document.getElementById('episode-modal').classList.add('hidden');
    currentEditEpisodeId = null;
}

// 保存子集
async function saveEpisode() {
    const episodeName = document.getElementById('episode-name').value.trim();
    if (!episodeName) {
        showError('节目名称不能为空');
        return;
    }
    
    const formData = {
        '节目名称': episodeName,
        '媒体拉取地址': document.getElementById('episode-media-url').value.trim() || '',
        '媒体类型': parseInt(document.getElementById('episode-media-type').value) || 0,
        '编码格式': parseInt(document.getElementById('episode-encoding').value) || 0,
        '集数': parseInt(document.getElementById('episode-number').value) || 0,
        '时长': parseInt(document.getElementById('episode-duration').value) || 0,
        '文件大小': parseInt(document.getElementById('episode-file-size').value) || 0
    };
    
    try {
        let url = `${API_BASE}/dramas/${currentDramaId}/episodes`;
        let method = 'POST';
        
        if (currentEditEpisodeId) {
            url = `${API_BASE}/dramas/${currentDramaId}/episodes/${currentEditEpisodeId}`;
            method = 'PUT';
        }
        
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        if (result.code === 200) {
            showSuccess(currentEditEpisodeId ? '子集更新成功！' : '子集添加成功！');
            closeEpisodeModal();
            // 重新加载详情页
            await refreshDramaDetail();
        } else {
            showError('操作失败：' + (result.message || '未知错误'));
        }
    } catch (error) {
        showError('操作失败：' + error.message);
    }
}

// 删除子集
async function deleteEpisode(episodeId, episodeName) {
    if (!confirm(`确定要删除子集"${episodeName}"吗？此操作不可恢复。`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/dramas/${currentDramaId}/episodes/${episodeId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.code === 200) {
            showSuccess('子集删除成功！');
            // 重新加载详情页
            await refreshDramaDetail();
        } else {
            showError('删除失败：' + (result.message || '未知错误'));
        }
    } catch (error) {
        showError('删除失败：' + error.message);
    }
}

// 刷新剧集详情页
async function refreshDramaDetail() {
    if (!currentDramaId) return;
    
    try {
        // 获取剧集详情
        const response = await fetch(`${API_BASE}/dramas/${currentDramaId}`);
        const result = await response.json();
        
        if (result.code === 200) {
            const header = result.data;
            currentDramaData = header;
            currentDramaName = header['剧集名称'];
            
            // 获取子集列表
            const episodesResponse = await fetch(`${API_BASE}/dramas/${currentDramaId}/episodes`);
            const episodesResult = await episodesResponse.json();
            const episodes = episodesResult.code === 200 ? episodesResult.data : [];
            
            // 重新渲染详情（在剧头管理页面内联显示）
            const resultContainer = document.getElementById('header-search-result');
            if (resultContainer) {
                renderDramaDetailInline(header, episodes, resultContainer);
            }
        }
    } catch (error) {
        showError('刷新失败：' + error.message);
    }
}


// ==================== Excel批量导入功能 ====================

// 导入状态
let importState = {
    step: 'upload',  // upload, preview, progress, complete
    taskId: null,
    file: null,
    previewData: null,
    errors: [],
    pollInterval: null,  // 轮询定时器
    isMinimized: false   // 是否最小化
};

// 下载版权方数据导入模板
async function downloadImportTemplate() {
    try {
        const response = await fetch(`${API_BASE}/copyright/template`);
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = '版权方数据导入模板.xlsx';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            showSuccess('模板下载成功！请填写数据后导入');
        } else {
            const result = await response.json();
            showError('下载模板失败：' + (result.detail || '未知错误'));
        }
    } catch (error) {
        showError('下载模板失败：' + error.message);
    }
}

// 打开导入模态框
function openImportModal() {
    // 重置状态
    importState = {
        step: 'upload',
        taskId: null,
        file: null,
        previewData: null,
        errors: [],
        pollInterval: null,
        isMinimized: false
    };
    
    // 重置UI
    showImportStep('upload');
    clearSelectedFile();
    document.getElementById('import-file-input').value = '';
    document.getElementById('import-btn-upload').disabled = true;
    
    document.getElementById('import-modal').classList.remove('hidden');
}

// 关闭导入模态框
function closeImportModal() {
    // 如果正在导入，只是隐藏窗口，不停止轮询
    if (importState.step === 'progress' && importState.pollInterval) {
        importState.isMinimized = true;
    }
    document.getElementById('import-modal').classList.add('hidden');
}

// 最小化导入模态框
function minimizeImportModal() {
    importState.isMinimized = true;
    document.getElementById('import-modal').classList.add('hidden');
    showSuccess('导入正在后台进行，完成后会自动刷新列表');
}

// 显示指定步骤
function showImportStep(step) {
    importState.step = step;
    
    // 隐藏所有步骤内容
    document.querySelectorAll('.import-step').forEach(el => el.classList.add('hidden'));
    
    // 显示当前步骤
    const stepEl = document.getElementById(`import-step-${step}`);
    if (stepEl) stepEl.classList.remove('hidden');
    
    // 更新步骤指示器
    const steps = ['upload', 'preview', 'progress', 'complete'];
    steps.forEach((s, idx) => {
        const stepIndicator = document.getElementById(`step-${s}`);
        if (!stepIndicator) return;
        
        const circle = stepIndicator.querySelector('div');
        const currentIdx = steps.indexOf(step);
        
        if (idx < currentIdx) {
            // 已完成
            stepIndicator.classList.remove('text-slate-400');
            stepIndicator.classList.add('text-green-600');
            circle.classList.remove('bg-slate-300', 'bg-purple-600');
            circle.classList.add('bg-green-600');
        } else if (idx === currentIdx) {
            // 当前
            stepIndicator.classList.remove('text-slate-400', 'text-green-600');
            stepIndicator.classList.add('text-purple-600');
            circle.classList.remove('bg-slate-300', 'bg-green-600');
            circle.classList.add('bg-purple-600');
        } else {
            // 未完成
            stepIndicator.classList.remove('text-purple-600', 'text-green-600');
            stepIndicator.classList.add('text-slate-400');
            circle.classList.remove('bg-purple-600', 'bg-green-600');
            circle.classList.add('bg-slate-300');
        }
    });
    
    // 更新按钮显示
    updateImportButtons(step);
}

// 更新按钮显示
function updateImportButtons(step) {
    const btnBack = document.getElementById('import-btn-back');
    const btnCancel = document.getElementById('import-btn-cancel');
    const btnUpload = document.getElementById('import-btn-upload');
    const btnConfirm = document.getElementById('import-btn-confirm');
    const btnClose = document.getElementById('import-btn-close');
    
    // 隐藏所有按钮
    btnBack.classList.add('hidden');
    btnUpload.classList.add('hidden');
    btnConfirm.classList.add('hidden');
    btnClose.classList.add('hidden');
    
    switch (step) {
        case 'upload':
            btnCancel.classList.remove('hidden');
            btnUpload.classList.remove('hidden');
            break;
        case 'preview':
            btnBack.classList.remove('hidden');
            btnCancel.classList.remove('hidden');
            btnConfirm.classList.remove('hidden');
            break;
        case 'progress':
            btnCancel.classList.add('hidden');
            break;
        case 'complete':
            btnClose.classList.remove('hidden');
            btnCancel.classList.add('hidden');
            break;
    }
}

// 处理拖拽悬停
function handleDragOver(event) {
    event.preventDefault();
    event.stopPropagation();
    const dropZone = document.getElementById('drop-zone');
    dropZone.classList.add('border-purple-500', 'bg-purple-50');
    dropZone.classList.remove('border-slate-300');
}

// 处理拖拽离开
function handleDragLeave(event) {
    event.preventDefault();
    event.stopPropagation();
    const dropZone = document.getElementById('drop-zone');
    dropZone.classList.remove('border-purple-500', 'bg-purple-50');
    dropZone.classList.add('border-slate-300');
}

// 处理文件拖放
function handleDrop(event) {
    event.preventDefault();
    event.stopPropagation();
    
    const dropZone = document.getElementById('drop-zone');
    dropZone.classList.remove('border-purple-500', 'bg-purple-50');
    dropZone.classList.add('border-slate-300');
    
    const files = event.dataTransfer.files;
    if (files.length > 0) {
        processFile(files[0]);
    }
}

// 处理文件选择
function handleFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;
    processFile(file);
}

// 处理文件（统一入口）
function processFile(file) {
    // 验证文件格式
    const ext = file.name.split('.').pop().toLowerCase();
    if (!['xlsx', 'xls'].includes(ext)) {
        showError('不支持的文件格式，仅支持 .xlsx, .xls');
        return;
    }
    
    // 验证文件大小
    if (file.size > 50 * 1024 * 1024) {
        showError('文件大小超过限制，最大允许 50MB');
        return;
    }
    
    importState.file = file;
    
    // 显示文件信息
    document.getElementById('selected-file-info').classList.remove('hidden');
    document.getElementById('selected-file-name').textContent = file.name;
    document.getElementById('selected-file-size').textContent = formatFileSize(file.size);
    
    // 启用上传按钮
    document.getElementById('import-btn-upload').disabled = false;
}

// 清除选中的文件
function clearSelectedFile() {
    importState.file = null;
    document.getElementById('selected-file-info').classList.add('hidden');
    document.getElementById('import-file-input').value = '';
    document.getElementById('import-btn-upload').disabled = true;
}

// 格式化文件大小
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

// 上传并解析文件
async function uploadImportFile() {
    if (!importState.file) {
        showError('请先选择文件');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', importState.file);
    
    try {
        document.getElementById('import-btn-upload').disabled = true;
        document.getElementById('import-btn-upload').textContent = '解析中...';
        
        const response = await fetch(`${API_BASE}/copyright/import/upload`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.code === 200) {
            importState.taskId = result.data.task_id;
            importState.previewData = result.data;
            
            // 显示预览
            showPreviewData(result.data);
            showImportStep('preview');
        } else {
            showError(result.detail || result.message || '文件解析失败');
        }
    } catch (error) {
        showError('上传失败：' + error.message);
    } finally {
        document.getElementById('import-btn-upload').disabled = false;
        document.getElementById('import-btn-upload').textContent = '上传并解析';
    }
}

// 显示预览数据
function showPreviewData(data) {
    // 更新统计
    document.getElementById('preview-total').textContent = data.total_rows || 0;
    document.getElementById('preview-valid').textContent = data.valid_rows || 0;
    document.getElementById('preview-duplicate').textContent = data.duplicate_rows || 0;
    document.getElementById('preview-existing').textContent = data.existing_in_db || 0;
    
    // 渲染预览表格
    const tbody = document.getElementById('preview-table-body');
    const samples = data.sample_data || [];
    
    if (samples.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="px-3 py-4 text-center text-slate-500">无有效数据</td></tr>';
    } else {
        tbody.innerHTML = samples.map(item => `
            <tr class="hover:bg-slate-50">
                <td class="px-3 py-2 text-slate-700">${item.media_name || '-'}</td>
                <td class="px-3 py-2 text-slate-600">${item.category_level1 || '-'}</td>
                <td class="px-3 py-2 text-slate-600">${item.episode_count || '-'}</td>
                <td class="px-3 py-2 text-slate-600">${item.upstream_copyright || '-'}</td>
            </tr>
        `).join('');
    }
    
    // 显示错误详情
    const errorsContainer = document.getElementById('preview-errors');
    const errorList = document.getElementById('preview-error-list');
    const invalidDetails = data.invalid_details || [];
    
    if (invalidDetails.length > 0) {
        errorsContainer.classList.remove('hidden');
        errorList.innerHTML = invalidDetails.slice(0, 20).map(err => 
            `<div>第 ${err.row} 行: ${err.reason}</div>`
        ).join('');
        if (invalidDetails.length > 20) {
            errorList.innerHTML += `<div class="mt-1 text-slate-500">... 还有 ${invalidDetails.length - 20} 条错误</div>`;
        }
    } else {
        errorsContainer.classList.add('hidden');
    }
}

// 返回上一步
function importStepBack() {
    if (importState.step === 'preview') {
        showImportStep('upload');
    }
}

// 确认导入
async function confirmImport() {
    if (!importState.taskId) {
        showError('任务不存在，请重新上传文件');
        return;
    }
    
    try {
        // 启动导入
        const response = await fetch(`${API_BASE}/copyright/import/execute/${importState.taskId}`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.code === 200) {
            showImportStep('progress');
            // 开始轮询进度
            pollImportProgress();
        } else {
            showError(result.detail || result.message || '启动导入失败');
        }
    } catch (error) {
        showError('启动导入失败：' + error.message);
    }
}

// 轮询导入进度
async function pollImportProgress() {
    if (!importState.taskId) return;
    
    // 清除之前的轮询
    if (importState.pollInterval) {
        clearInterval(importState.pollInterval);
    }
    
    importState.pollInterval = setInterval(async () => {
        try {
            const response = await fetch(`${API_BASE}/copyright/import/status/${importState.taskId}`);
            const result = await response.json();
            
            if (result.code === 200) {
                const data = result.data;
                
                // 更新进度显示（即使窗口最小化也更新状态）
                if (!importState.isMinimized) {
                    document.getElementById('progress-percentage').textContent = data.percentage + '%';
                    document.getElementById('progress-bar').style.width = data.percentage + '%';
                    document.getElementById('progress-success').textContent = data.success || 0;
                    document.getElementById('progress-skipped').textContent = data.skipped || 0;
                    document.getElementById('progress-failed').textContent = data.failed || 0;
                }
                
                // 检查是否完成
                if (data.status === 'completed' || data.status === 'failed') {
                    clearInterval(importState.pollInterval);
                    importState.pollInterval = null;
                    
                    // 自动刷新列表
                    loadCopyrightContent();
                    
                    // 如果窗口最小化，显示通知
                    if (importState.isMinimized) {
                        if (data.status === 'completed') {
                            showSuccess(`导入完成！成功 ${data.success} 条，跳过 ${data.skipped} 条，失败 ${data.failed} 条`);
                        } else {
                            showError('导入失败，请重新尝试');
                        }
                        importState.isMinimized = false;
                    } else {
                        showImportComplete(data);
                    }
                }
            }
        } catch (error) {
            console.error('轮询进度失败:', error);
        }
    }, 500);  // 每0.5秒检查一次，提高响应速度
}

// 显示导入完成
function showImportComplete(data) {
    showImportStep('complete');
    
    // 更新统计
    document.getElementById('complete-success').textContent = data.success || 0;
    document.getElementById('complete-skipped').textContent = data.skipped || 0;
    document.getElementById('complete-failed').textContent = data.failed || 0;
    
    // 更新标题和图标
    const icon = document.getElementById('complete-icon');
    const title = document.getElementById('complete-title');
    const elapsedEl = document.getElementById('complete-elapsed');
    
    if (data.status === 'failed') {
        icon.classList.remove('bg-green-100');
        icon.classList.add('bg-red-100');
        icon.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-red-600"><line x1="18" x2="6" y1="6" y2="18"/><line x1="6" x2="18" y1="6" y2="18"/></svg>';
        title.textContent = '导入失败';
    } else {
        icon.classList.remove('bg-red-100');
        icon.classList.add('bg-green-100');
        icon.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-green-600"><polyline points="20 6 9 17 4 12"/></svg>';
        title.textContent = '导入完成';
        
        // 显示子集生成状态
        const episodeStatus = data.episode_generation_status || '';
        if (episodeStatus === 'pending' || episodeStatus === 'running') {
            elapsedEl.innerHTML = `<span class="text-blue-600">📦 子集正在后台生成中... (${data.episode_generation_progress || 0}%)</span>`;
            // 继续轮询子集生成进度
            startEpisodeGenerationPolling();
        } else if (episodeStatus === 'completed') {
            elapsedEl.textContent = '✅ 版权数据和子集均已生成完成';
        } else if (episodeStatus === 'failed') {
            elapsedEl.innerHTML = '<span class="text-orange-600">⚠️ 版权数据已导入，但子集生成失败</span>';
        } else {
            elapsedEl.textContent = '';
        }
    }
    
    // 显示错误详情
    const errorsContainer = document.getElementById('complete-errors');
    const errorList = document.getElementById('complete-error-list');
    const errors = data.errors || [];
    importState.errors = errors;
    
    if (errors.length > 0) {
        errorsContainer.classList.remove('hidden');
        errorList.innerHTML = errors.slice(0, 20).map(err => 
            `<div>${err.media_name ? `"${err.media_name}"` : `第 ${err.row || err.batch} 行`}: ${err.message}</div>`
        ).join('');
        if (errors.length > 20) {
            errorList.innerHTML += `<div class="mt-1 text-slate-500">... 还有 ${errors.length - 20} 条错误</div>`;
        }
    } else {
        errorsContainer.classList.add('hidden');
    }
}

// 导出错误数据
function exportErrors() {
    if (!importState.errors || importState.errors.length === 0) {
        showError('没有错误数据可导出');
        return;
    }
    
    // 生成CSV内容
    let csv = '行号,介质名称,错误信息\n';
    importState.errors.forEach(err => {
        const row = err.row || err.batch || '';
        const name = (err.media_name || '').replace(/"/g, '""');
        const msg = (err.message || '').replace(/"/g, '""');
        csv += `"${row}","${name}","${msg}"\n`;
    });
    
    // 下载文件
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = '导入错误数据.csv';
    a.click();
    URL.revokeObjectURL(url);
}

// 子集生成进度轮询
let episodeGenerationPollInterval = null;

function startEpisodeGenerationPolling() {
    if (episodeGenerationPollInterval) {
        clearInterval(episodeGenerationPollInterval);
    }
    
    const elapsedEl = document.getElementById('complete-elapsed');
    
    episodeGenerationPollInterval = setInterval(async () => {
        try {
            const response = await fetch(`${API_BASE}/copyright/import/status/${importState.taskId}`);
            const result = await response.json();
            
            if (result.code === 200) {
                const data = result.data;
                const status = data.episode_generation_status || '';
                const progress = data.episode_generation_progress || 0;
                
                if (status === 'running' || status === 'pending') {
                    elapsedEl.innerHTML = `<span class="text-blue-600">📦 子集正在后台生成中... (${progress}%)</span>`;
                } else if (status === 'completed') {
                    elapsedEl.innerHTML = '<span class="text-green-600">✅ 版权数据和子集均已生成完成</span>';
                    clearInterval(episodeGenerationPollInterval);
                    episodeGenerationPollInterval = null;
                } else if (status === 'failed') {
                    elapsedEl.innerHTML = '<span class="text-orange-600">⚠️ 版权数据已导入，但子集生成失败</span>';
                    clearInterval(episodeGenerationPollInterval);
                    episodeGenerationPollInterval = null;
                }
            }
        } catch (error) {
            console.error('轮询子集生成进度失败:', error);
        }
    }, 1000);  // 每秒检查一次
}

// 加载版权方数据（用于导入完成后刷新）
function loadCopyrightContent() {
    loadCopyrightList(1);
}
// ============================================================
