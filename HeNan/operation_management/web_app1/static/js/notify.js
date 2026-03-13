/**
 * 邮件提醒配置页面交互
 */

function _getNotifyRecipientsFromInput() {
    const el = document.getElementById('notify-recipients');
    if (!el) return [];
    return el.value
        .replace(/\n/g, ',')
        .split(',')
        .map((item) => item.trim())
        .filter((item) => item);
}

function _withNoCache(url) {
    const sep = url.includes('?') ? '&' : '?';
    return `${url}${sep}_t=${Date.now()}`;
}

function _clampScheduleDay(raw) {
    const n = Number(raw);
    if (!Number.isFinite(n)) return 1;
    return Math.max(1, Math.min(28, Math.floor(n)));
}

function _normalizeScheduleTime(raw) {
    const text = String(raw || '').trim();
    if (!/^\d{2}:\d{2}$/.test(text)) return '09:00';
    return text;
}

function _updateNotifyCronExpression() {
    const dayEl = document.getElementById('notify-schedule-day');
    const timeEl = document.getElementById('notify-schedule-time');
    const cronEl = document.getElementById('notify-cron-expression');
    if (!dayEl || !timeEl || !cronEl) return;

    const day = _clampScheduleDay(dayEl.value);
    const timeValue = _normalizeScheduleTime(timeEl.value);
    const [hh, mm] = timeValue.split(':');

    dayEl.value = day;
    timeEl.value = timeValue;
    cronEl.value = `0 ${mm} ${hh} ${day} * *`;
}

function _bindNotifyScheduleEditors() {
    const dayEl = document.getElementById('notify-schedule-day');
    const timeEl = document.getElementById('notify-schedule-time');
    if (!dayEl || !timeEl) return;
    if (!dayEl.dataset.boundCron) {
        dayEl.addEventListener('input', _updateNotifyCronExpression);
        dayEl.addEventListener('change', _updateNotifyCronExpression);
        dayEl.dataset.boundCron = '1';
    }
    if (!timeEl.dataset.boundCron) {
        timeEl.addEventListener('input', _updateNotifyCronExpression);
        timeEl.addEventListener('change', _updateNotifyCronExpression);
        timeEl.dataset.boundCron = '1';
    }
}

function _renderNotifyPreview(data) {
    const bodyEl = document.getElementById('notify-preview-body');
    if (!bodyEl) return;

    const rows = data?.records || [];
    if (!rows.length) {
        bodyEl.innerHTML = '<tr><td colspan="5" class="px-4 py-6 text-center notify-preview-cell-muted">暂无即将到期版权记录</td></tr>';
        return;
    }

    bodyEl.innerHTML = rows.map((row) => `
        <tr class="border-b border-slate-100">
            <td class="px-4 py-2 text-sm notify-preview-cell-main">${row.media_name || '-'}</td>
            <td class="px-4 py-2 text-sm notify-preview-cell-muted">${row.operator_name || '-'}</td>
            <td class="px-4 py-2 text-sm notify-preview-cell-muted">${row.upstream_copyright || '-'}</td>
            <td class="px-4 py-2 text-sm notify-preview-cell-muted">${row.copyright_start_date || '-'}</td>
            <td class="px-4 py-2 text-sm notify-preview-cell-end">${row.copyright_end_date || '-'}</td>
        </tr>
    `).join('');
}

function _renderNotifyStatus(data) {
    const schedulerEl = document.getElementById('notify-status-scheduler');
    const nextRunEl = document.getElementById('notify-status-next-run');
    const lastResultEl = document.getElementById('notify-status-last-result');
    const lastSentEl = document.getElementById('notify-status-last-sent');
    const lastCountEl = document.getElementById('notify-status-last-count');
    const lastErrorEl = document.getElementById('notify-status-last-error');

    if (!schedulerEl || !nextRunEl || !lastResultEl || !lastSentEl || !lastCountEl || !lastErrorEl) return;

    const state = data?.state || {};
    schedulerEl.textContent = data?.scheduler_running ? '运行中' : '未运行';
    nextRunEl.textContent = data?.scheduler_next_run || '-';
    lastResultEl.textContent = state.last_result || '-';
    lastSentEl.textContent = state.last_sent_at || '-';
    lastCountEl.textContent = String(state.last_count ?? '-');
    lastErrorEl.textContent = state.last_error || '-';
}

async function loadNotifyConfig() {
    const response = await fetch(_withNoCache(`${API_BASE}/notify/config`), { cache: 'no-store' });
    const result = await response.json();
    if (result.code !== 200) {
        throw new Error(result.message || '加载配置失败');
    }

    const cfg = result.data || {};
    const smtp = cfg.smtp || {};

    const host = document.getElementById('notify-smtp-host');
    const port = document.getElementById('notify-smtp-port');
    const tls = document.getElementById('notify-smtp-tls');
    const username = document.getElementById('notify-smtp-username');
    const password = document.getElementById('notify-smtp-password');
    const fromName = document.getElementById('notify-from-name');
    const recipients = document.getElementById('notify-recipients');
    const scheduleDay = document.getElementById('notify-schedule-day');
    const scheduleTime = document.getElementById('notify-schedule-time');

    if (host) host.value = smtp.host || '';
    if (port) port.value = smtp.port || 587;
    if (tls) tls.checked = !!smtp.use_tls;
    if (username) username.value = smtp.username || '';
    if (password) {
        password.value = '';
        password.placeholder = smtp.password_configured ? '已配置，留空表示不修改' : '请输入SMTP授权码';
    }
    if (fromName) fromName.value = smtp.from_name || '运营管理平台';
    if (recipients) recipients.value = (cfg.recipients || []).join('\n');
    if (scheduleDay) {
        scheduleDay.value = _clampScheduleDay(cfg.schedule && cfg.schedule.day);
    }
    if (scheduleTime) scheduleTime.value = _normalizeScheduleTime((cfg.schedule && cfg.schedule.time) ? cfg.schedule.time : '09:00');

    _bindNotifyScheduleEditors();
    _updateNotifyCronExpression();
}

async function loadNotifyPreview() {
    const response = await fetch(_withNoCache(`${API_BASE}/notify/preview`), { cache: 'no-store' });
    const result = await response.json();
    if (result.code !== 200) {
        throw new Error(result.message || '加载预览失败');
    }
    _renderNotifyPreview(result.data || {});
}

async function loadNotifyStatus() {
    const response = await fetch(_withNoCache(`${API_BASE}/notify/status`), { cache: 'no-store' });
    const result = await response.json();
    if (result.code !== 200) {
        throw new Error(result.message || '加载状态失败');
    }
    _renderNotifyStatus(result.data || {});
}

async function loadNotifyPageData() {
    try {
        await Promise.all([loadNotifyConfig(), loadNotifyPreview(), loadNotifyStatus()]);
    } catch (error) {
        showError(error.message || '加载邮件提醒页面失败');
    }
}

async function saveNotifyConfig() {
    try {
        const scheduleDayValue = _clampScheduleDay(document.getElementById('notify-schedule-day')?.value || 1);
        const scheduleTimeValue = _normalizeScheduleTime(document.getElementById('notify-schedule-time')?.value || '09:00');

        const scheduleDayEl = document.getElementById('notify-schedule-day');
        const scheduleTimeEl = document.getElementById('notify-schedule-time');
        if (scheduleDayEl) scheduleDayEl.value = scheduleDayValue;
        if (scheduleTimeEl) scheduleTimeEl.value = scheduleTimeValue;
        _updateNotifyCronExpression();

        const payload = {
            enabled: true,
            smtp: {
                host: document.getElementById('notify-smtp-host')?.value?.trim() || '',
                port: Number(document.getElementById('notify-smtp-port')?.value || 587),
                use_tls: !!document.getElementById('notify-smtp-tls')?.checked,
                username: document.getElementById('notify-smtp-username')?.value?.trim() || '',
                password: document.getElementById('notify-smtp-password')?.value || '',
                from_name: document.getElementById('notify-from-name')?.value?.trim() || '运营管理平台',
            },
            recipients: _getNotifyRecipientsFromInput(),
            schedule: {
                day: scheduleDayValue,
                time: scheduleTimeValue,
            },
            rule: {
                months_before_expiry: 1,
            },
        };

        const response = await fetch(`${API_BASE}/notify/config`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        const result = await response.json();

        if (result.code !== 200) {
            throw new Error(result.message || '保存配置失败');
        }

        showSuccess('邮件提醒配置已保存');
        await Promise.all([loadNotifyConfig(), loadNotifyStatus()]);
    } catch (error) {
        showError(error.message || '保存配置失败');
    }
}

async function sendNotifyTestEmail() {
    try {
        const response = await fetch(`${API_BASE}/notify/test`, { method: 'POST' });
        const result = await response.json();
        if (result.code !== 200) {
            throw new Error(result.message || '测试邮件发送失败');
        }
        showSuccess(result.message || '测试邮件发送成功');
        await loadNotifyStatus();
    } catch (error) {
        showError(error.message || '测试邮件发送失败');
    }
}

