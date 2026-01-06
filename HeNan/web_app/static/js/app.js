/**
 * 剧集数据查询系统 - 前端JavaScript
 */

// API基础URL
const API_BASE = '';

// 全局变量
let currentDramaName = '';
let allDramas = [];

// DOM元素
const searchInput = document.getElementById('searchInput');
const searchBtn = document.getElementById('searchBtn');
const showAllBtn = document.getElementById('showAllBtn');
const suggestions = document.getElementById('suggestions');
const loadingState = document.getElementById('loadingState');
const errorState = document.getElementById('errorState');
const errorMessage = document.getElementById('errorMessage');
const resultSection = document.getElementById('resultSection');
const dramaHeaderInfo = document.getElementById('dramaHeaderInfo');
const episodesTableBody = document.getElementById('episodesTableBody');
const episodeCount = document.getElementById('episodeCount');
const exportBtn = document.getElementById('exportBtn');
const dramaListModal = document.getElementById('dramaListModal');
const dramaList = document.getElementById('dramaList');
const closeModalBtn = document.getElementById('closeModalBtn');
const toast = document.getElementById('toast');

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
    loadDramaList();
});

// 初始化事件监听
function initEventListeners() {
    // 搜索按钮点击
    searchBtn.addEventListener('click', handleSearch);
    
    // 输入框回车搜索
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            handleSearch();
        }
    });
    
    // 输入框输入事件（搜索建议）
    searchInput.addEventListener('input', handleInputChange);
    
    // 点击其他地方关闭建议框
    document.addEventListener('click', (e) => {
        if (!searchInput.contains(e.target) && !suggestions.contains(e.target)) {
            suggestions.classList.add('hidden');
        }
    });
    
    // 显示所有剧集按钮
    showAllBtn.addEventListener('click', showDramaListModal);
    
    // 关闭弹窗
    closeModalBtn.addEventListener('click', () => {
        dramaListModal.classList.add('hidden');
    });
    
    // 点击弹窗背景关闭
    dramaListModal.addEventListener('click', (e) => {
        if (e.target === dramaListModal) {
            dramaListModal.classList.add('hidden');
        }
    });
    
    // 导出按钮
    exportBtn.addEventListener('click', handleExport);
}

// 加载剧集列表
async function loadDramaList() {
    try {
        const response = await fetch(`${API_BASE}/api/drama/list`);
        const data = await response.json();
        
        if (data.success) {
            allDramas = data.data;
        }
    } catch (error) {
        console.error('加载剧集列表失败:', error);
    }
}

// 处理输入变化（搜索建议）
function handleInputChange() {
    const value = searchInput.value.trim();
    
    if (!value) {
        suggestions.classList.add('hidden');
        return;
    }
    
    // 过滤匹配的剧集
    const filtered = allDramas.filter(drama => 
        drama.name.toLowerCase().includes(value.toLowerCase())
    );
    
    if (filtered.length > 0) {
        renderSuggestions(filtered);
        suggestions.classList.remove('hidden');
    } else {
        suggestions.classList.add('hidden');
    }
}

// 渲染搜索建议
function renderSuggestions(dramas) {
    suggestions.innerHTML = dramas.map(drama => `
        <div class="suggestion-item" data-name="${escapeHtml(drama.name)}">
            🎬 ${escapeHtml(drama.name)}
        </div>
    `).join('');
    
    // 添加点击事件
    suggestions.querySelectorAll('.suggestion-item').forEach(item => {
        item.addEventListener('click', () => {
            searchInput.value = item.dataset.name;
            suggestions.classList.add('hidden');
            handleSearch();
        });
    });
}

// 处理搜索
async function handleSearch() {
    const name = searchInput.value.trim();
    
    if (!name) {
        showToast('请输入剧集名称', 'error');
        return;
    }
    
    currentDramaName = name;
    
    // 显示加载状态
    showLoading(true);
    hideError();
    hideResult();
    
    try {
        const response = await fetch(`${API_BASE}/api/drama/search?name=${encodeURIComponent(name)}`);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || '查询失败');
        }
        
        if (data.success) {
            renderResult(data.data);
            showResult();
            showToast('查询成功！', 'success');
        }
    } catch (error) {
        showError(error.message);
    } finally {
        showLoading(false);
    }
}

// 渲染查询结果
function renderResult(data) {
    // 渲染剧头信息
    renderDramaHeader(data.drama_header);
    
    // 渲染子集数据
    renderEpisodes(data.episodes);
    
    // 更新集数显示
    episodeCount.textContent = `共 ${data.episode_count} 集`;
}

// 渲染剧头信息
function renderDramaHeader(header) {
    const infoItems = [
        { label: '剧头ID', value: header['剧头id'], highlight: true },
        { label: '剧集名称', value: header['剧集名称'], highlight: true },
        { label: '内容类型', value: header['内容类型'] },
        { label: '二级分类', value: header['二级分类'] },
        { label: '作者列表', value: header['作者列表'] },
        { label: '主演', value: header['主演'] },
        { label: '语言', value: header['语言'] },
        { label: '上映年份', value: header['上映年份'] },
        { label: '总集数', value: header['总集数'] },
        { label: '评分', value: header['评分'] },
        { label: '清晰度', value: getClarity(header['清晰度']) },
        { label: '产品分类', value: getProductCategory(header['产品分类']) },
        { label: '版权', value: getCopyright(header['版权']) },
        { label: '关键字', value: header['关键字'] },
        { label: '推荐语', value: header['推荐语'] },
        { label: '描述', value: header['描述'] },
        { label: '竖图', value: header['竖图'], isUrl: true },
        { label: '横图', value: header['横图'], isUrl: true }
    ];
    
    dramaHeaderInfo.innerHTML = infoItems.map(item => `
        <div class="info-item">
            <span class="info-label">${item.label}</span>
            <span class="info-value ${item.highlight ? 'highlight' : ''}">${
                item.isUrl && item.value 
                    ? `<a href="${escapeHtml(item.value)}" target="_blank" style="color: var(--primary-color); word-break: break-all;">${escapeHtml(item.value)}</a>`
                    : escapeHtml(String(item.value || '-'))
            }</span>
        </div>
    `).join('');
}

// 渲染子集数据
function renderEpisodes(episodes) {
    if (!episodes || episodes.length === 0) {
        episodesTableBody.innerHTML = `
            <tr>
                <td colspan="8" style="text-align: center; padding: 2rem; color: var(--text-secondary);">
                    暂无子集数据
                </td>
            </tr>
        `;
        return;
    }
    
    episodesTableBody.innerHTML = episodes.map(ep => `
        <tr>
            <td>${ep['子集id']}</td>
            <td>${escapeHtml(ep['节目名称'])}</td>
            <td>${getMediaType(ep['媒体类型'])}</td>
            <td>${getEncodingFormat(ep['编码格式'])}</td>
            <td>${ep['集数']}</td>
            <td>${formatDuration(ep['时长'])}</td>
            <td>${formatFileSize(ep['文件大小'])}</td>
            <td class="url-cell" title="${escapeHtml(ep['媒体拉取地址'])}">${escapeHtml(ep['媒体拉取地址'])}</td>
        </tr>
    `).join('');
}

// 处理导出
async function handleExport() {
    if (!currentDramaName) {
        showToast('请先查询剧集', 'error');
        return;
    }
    
    showToast('正在生成Excel文件...', 'success');
    
    try {
        const response = await fetch(`${API_BASE}/api/drama/export?name=${encodeURIComponent(currentDramaName)}`);
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '导出失败');
        }
        
        // 直接使用剧集名称构建文件名，避免解析 Content-Disposition header 的问题
        const filename = `${currentDramaName}_数据.xlsx`;
        
        // 下载文件
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        showToast('导出成功！', 'success');
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// 显示剧集列表弹窗
function showDramaListModal() {
    if (allDramas.length === 0) {
        showToast('暂无剧集数据', 'error');
        return;
    }
    
    dramaList.innerHTML = allDramas.map(drama => `
        <li data-name="${escapeHtml(drama.name)}">
            <span>🎬</span>
            <span>${escapeHtml(drama.name)}</span>
        </li>
    `).join('');
    
    // 添加点击事件
    dramaList.querySelectorAll('li').forEach(item => {
        item.addEventListener('click', () => {
            searchInput.value = item.dataset.name;
            dramaListModal.classList.add('hidden');
            handleSearch();
        });
    });
    
    dramaListModal.classList.remove('hidden');
}

// 工具函数

// 显示/隐藏加载状态
function showLoading(show) {
    if (show) {
        loadingState.classList.remove('hidden');
    } else {
        loadingState.classList.add('hidden');
    }
}

// 显示错误
function showError(message) {
    errorMessage.textContent = message;
    errorState.classList.remove('hidden');
}

// 隐藏错误
function hideError() {
    errorState.classList.add('hidden');
}

// 显示结果
function showResult() {
    resultSection.classList.remove('hidden');
}

// 隐藏结果
function hideResult() {
    resultSection.classList.add('hidden');
}

// 显示Toast
function showToast(message, type = '') {
    toast.textContent = message;
    toast.className = `toast ${type}`;
    toast.classList.remove('hidden');
    
    setTimeout(() => {
        toast.classList.add('hidden');
    }, 3000);
}

// HTML转义
function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// 格式化时长
function formatDuration(seconds) {
    if (!seconds) return '-';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${String(secs).padStart(2, '0')}`;
}

// 格式化文件大小
function formatFileSize(bytes) {
    if (!bytes) return '-';
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;
    while (size >= 1024 && unitIndex < units.length - 1) {
        size /= 1024;
        unitIndex++;
    }
    return `${size.toFixed(2)} ${units[unitIndex]}`;
}

// 清晰度映射
function getClarity(code) {
    const map = {
        0: '标清',
        1: '高清',
        2: '流超清',
        3: '4K',
        4: '杜比'
    };
    return map[code] || code;
}

// 产品分类映射
function getProductCategory(code) {
    const map = {
        1: '萌趣学堂（教育）',
        2: '荣耀王国（电竞）',
        3: '大包（少儿）'
    };
    return map[code] || code;
}

// 版权映射
function getCopyright(code) {
    const map = {
        0: '全部',
        1: '机顶盒',
        101: '智能电视',
        301: '投影仪',
        401: '音响',
        501: '云电脑',
        601: '闺蜜机',
        701: '云pad'
    };
    return map[code] || code;
}

// 媒体类型映射
function getMediaType(code) {
    const map = {
        1: '视频',
        2: '音频'
    };
    return map[code] || code;
}

// 编码格式映射
function getEncodingFormat(code) {
    const map = {
        1: 'H.264',
        2: 'H.265'
    };
    return map[code] || code;
}
