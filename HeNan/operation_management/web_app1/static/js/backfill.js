/**
 * 回填模块（backfill）
 *
 * 职责：
 * - “回填扫描字段/校正重算”弹窗交互
 * - 回填范围与字段收集（单剧名/全库）
 * - 启动回填任务与进度轮询展示
 * - 根据目标剧名数量限制“校正重算”模式
 *
 * 依赖关系：
 * - 依赖 common.js（API_BASE、showToast）
 * - 依赖 copyright.js 中的 backfillTaskState 状态对象
 */

function openBackfillModal() {
    document.getElementById('backfill-modal').classList.remove('hidden');
    resetBackfillState();
    updateBackfillTargetCount();
}

function closeBackfillModal() {
    document.getElementById('backfill-modal').classList.add('hidden');
    resetBackfillState();
}

function resetBackfillState() {
    if (backfillTaskState.pollTimer) {
        clearInterval(backfillTaskState.pollTimer);
        backfillTaskState.pollTimer = null;
    }
    backfillTaskState.taskId = null;

    const progressWrap = document.getElementById('backfill-progress');
    if (progressWrap) progressWrap.classList.add('hidden');

    const startBtn = document.getElementById('backfill-start-btn');
    if (startBtn) {
        startBtn.disabled = false;
        startBtn.innerHTML = '启动回填';
    }

    const correctBtn = document.getElementById('backfill-correct-btn');
    if (correctBtn) {
        correctBtn.disabled = true;
    }

    const statusEl = document.getElementById('backfill-status-text');
    if (statusEl) statusEl.textContent = '任务执行中...';
    const percentEl = document.getElementById('backfill-percentage');
    if (percentEl) percentEl.textContent = '0%';
    const bar = document.getElementById('backfill-progress-bar');
    if (bar) bar.style.width = '0%';

    ['matched', 'updated', 'missed', 'skipped'].forEach((key) => {
        const el = document.getElementById(`backfill-${key}`);
        if (el) el.textContent = '0';
    });

    const strategyEl = document.getElementById('backfill-strategy-text');
    if (strategyEl) {
        strategyEl.textContent = '回填模式：仅回填空值，不覆盖已有值。';
    }

    const selectedHint = document.getElementById('backfill-selected-hint');
    if (selectedHint) {
        selectedHint.classList.add('hidden');
        selectedHint.textContent = '';
    }

    const scopeSingle = document.querySelector('input[name="backfill-scope"][value="single"]');
    if (scopeSingle) scopeSingle.checked = true;
    onBackfillScopeChange();
}

function getSelectedDramaNamesForBackfill() {
    const selected = [];
    try {
        if (typeof batchSelectionState !== 'undefined' && batchSelectionState?.selectedDramas instanceof Set) {
            batchSelectionState.selectedDramas.forEach((name) => {
                const value = String(name || '').trim();
                if (value) selected.push(value);
            });
        }
    } catch (error) {
        console.warn('读取已选剧集失败:', error);
    }
    return [...new Set(selected)];
}

function updateBackfillActionState(targetCount, selectedNamesCount) {
    const correctBtn = document.getElementById('backfill-correct-btn');
    const strategyEl = document.getElementById('backfill-strategy-text');
    const selectedHint = document.getElementById('backfill-selected-hint');

    if (selectedHint) {
        if (selectedNamesCount > 0) {
            selectedHint.classList.remove('hidden');
            selectedHint.textContent = `已检测到前序页面选中剧集 ${selectedNamesCount} 个，将优先按已选剧集执行。`;
        } else {
            selectedHint.classList.add('hidden');
            selectedHint.textContent = '';
        }
    }

    const canRecalculate = targetCount === 1;
    if (correctBtn) {
        correctBtn.disabled = !canRecalculate;
    }

    if (strategyEl) {
        if (canRecalculate) {
            strategyEl.textContent = '当前可用两种模式：回填空值，或对该剧名执行全量校正重算。';
        } else if (targetCount === 0) {
            strategyEl.textContent = '请先选择目标剧名；单个剧名可校正重算，多个剧名仅支持回填空值。';
        } else {
            strategyEl.textContent = '当前目标为多个剧名，仅支持回填空值（MD5/时长/文件大小）。';
        }
    }
}

function onBackfillScopeChange() {
    const scope = document.querySelector('input[name="backfill-scope"]:checked')?.value || 'single';
    const singleWrap = document.getElementById('backfill-single-wrap');
    if (singleWrap) {
        singleWrap.classList.toggle('hidden', scope !== 'single');
    }
    updateBackfillTargetCount();
}

async function updateBackfillTargetCount() {
    const countEl = document.getElementById('backfill-target-count');
    if (!countEl) return;

    const selectedNames = getSelectedDramaNamesForBackfill();
    if (selectedNames.length > 0) {
        countEl.textContent = String(selectedNames.length);
        updateBackfillActionState(selectedNames.length, selectedNames.length);
        return;
    }

    const scope = document.querySelector('input[name="backfill-scope"]:checked')?.value || 'single';
    if (scope === 'single') {
        const value = document.getElementById('backfill-media-name')?.value?.trim() || '';
        countEl.textContent = value ? '1' : '0';
        updateBackfillActionState(value ? 1 : 0, 0);
        return;
    }

    countEl.textContent = '...';
    try {
        const response = await fetch(`${API_BASE}/copyright?page=1&page_size=1`);
        const result = await response.json();
        if (result.code === 200) {
            countEl.textContent = ((result.data && result.data.total) || 0).toLocaleString();
            updateBackfillActionState((result.data && result.data.total) || 0, 0);
        } else {
            countEl.textContent = '0';
            updateBackfillActionState(0, 0);
        }
    } catch (error) {
        console.error('获取回填目标数量失败:', error);
        countEl.textContent = '0';
        updateBackfillActionState(0, 0);
    }
}

async function collectBackfillMediaNames() {
    const selectedNames = getSelectedDramaNamesForBackfill();
    if (selectedNames.length > 0) {
        return selectedNames;
    }

    const scope = document.querySelector('input[name="backfill-scope"]:checked')?.value || 'single';
    if (scope === 'single') {
        const value = document.getElementById('backfill-media-name')?.value?.trim() || '';
        return value ? [value] : [];
    }

    const pageSizeForFetch = 100;
    let page = 1;
    let totalPages = 1;
    const names = [];

    while (page <= totalPages) {
        const url = `${API_BASE}/copyright?page=${page}&page_size=${pageSizeForFetch}`;

        const response = await fetch(url);
        const result = await response.json();
        if (result.code !== 200) {
            throw new Error(result.message || '获取所有搜索结果失败');
        }

        const data = result.data || {};
        const list = data.list || [];
        list.forEach((item) => {
            const name = (item?.media_name || '').trim();
            if (name) {
                names.push(name);
            }
        });

        totalPages = data.total_pages || 1;
        page += 1;
    }

    return [...new Set(names)];
}

function collectBackfillFields() {
    const fields = [];
    if (document.getElementById('backfill-field-md5')?.checked) fields.push('md5');
    if (document.getElementById('backfill-field-duration')?.checked) fields.push('duration');
    if (document.getElementById('backfill-field-size')?.checked) fields.push('size');
    return fields;
}

async function startScanBackfillTask(mode = 'only_empty') {
    const startBtn = document.getElementById('backfill-start-btn');
    const correctBtn = document.getElementById('backfill-correct-btn');
    const progressWrap = document.getElementById('backfill-progress');
    const statusEl = document.getElementById('backfill-status-text');

    startBtn.disabled = true;
    startBtn.innerHTML = mode === 'recalculate_all' ? '校正启动中...' : '启动中...';
    if (correctBtn) {
        correctBtn.disabled = true;
    }
    progressWrap.classList.remove('hidden');
    if (statusEl) statusEl.textContent = '正在启动任务...';

    try {
        const mediaNames = await collectBackfillMediaNames();
        const fields = mode === 'recalculate_all' ? ['md5', 'duration', 'size'] : collectBackfillFields();

        if (!mediaNames.length) {
            throw new Error('请先选择回填范围并提供有效剧名');
        }
        if (mode === 'recalculate_all' && mediaNames.length !== 1) {
            throw new Error('校正模式仅支持单个剧名，请只选择一个剧集');
        }
        if (!fields.length) {
            throw new Error('请至少选择一个回填字段');
        }

        const response = await fetch(`${API_BASE}/copyright/backfill/scan-fields/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ media_names: mediaNames, fields, mode })
        });
        const result = await response.json();
        if (result.code !== 200) {
            throw new Error(result.detail || result.message || '启动回填失败');
        }

        backfillTaskState.taskId = result.data.task_id;
        startBtn.innerHTML = mode === 'recalculate_all' ? '校正执行中...' : '回填执行中...';
        showToast(
            `${mode === 'recalculate_all' ? '校正' : '回填'}任务已启动，剧名数：${result.data.total_media}`,
            'success'
        );
        startBackfillPolling();
    } catch (error) {
        console.error('启动回填失败:', error);
        showToast(error.message || '启动回填失败', 'error');
        startBtn.disabled = false;
        startBtn.innerHTML = '启动回填';
        updateBackfillTargetCount();
    }
}

function startBackfillPolling() {
    if (backfillTaskState.pollTimer) {
        clearInterval(backfillTaskState.pollTimer);
    }

    const poll = async () => {
        if (!backfillTaskState.taskId) return;
        try {
            const response = await fetch(`${API_BASE}/copyright/backfill/scan-fields/status/${backfillTaskState.taskId}`);
            const result = await response.json();
            if (result.code !== 200) {
                return;
            }

            const data = result.data || {};
            document.getElementById('backfill-percentage').textContent = `${data.percentage || 0}%`;
            document.getElementById('backfill-progress-bar').style.width = `${data.percentage || 0}%`;
            document.getElementById('backfill-matched').textContent = (data.matched_episodes || 0).toLocaleString();
            document.getElementById('backfill-updated').textContent = (data.updated_episodes || 0).toLocaleString();
            document.getElementById('backfill-missed').textContent = (data.missed_episodes || 0).toLocaleString();
            document.getElementById('backfill-skipped').textContent = (data.skipped_episodes || 0).toLocaleString();

            const statusEl = document.getElementById('backfill-status-text');
            statusEl.textContent = `状态：${data.status}（${data.processed_media || 0}/${data.total_media || 0}）`;

            if (data.status === 'completed' || data.status === 'failed') {
                clearInterval(backfillTaskState.pollTimer);
                backfillTaskState.pollTimer = null;

                const startBtn = document.getElementById('backfill-start-btn');
                startBtn.disabled = false;
                startBtn.innerHTML = '启动回填';

                updateBackfillTargetCount();

                if (data.status === 'completed') {
                    const modeText = data.mode === 'recalculate_all' ? '校正完成' : '回填完成';
                    showToast(`${modeText}：更新${data.updated_episodes || 0}，未命中${data.missed_episodes || 0}`, 'success', 5000);
                } else {
                    showToast('回填任务失败，请查看日志', 'error');
                }
            }
        } catch (error) {
            console.error('轮询回填进度失败:', error);
        }
    };

    poll();
    backfillTaskState.pollTimer = setInterval(poll, 1000);
}
