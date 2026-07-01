document.addEventListener('DOMContentLoaded', () => {

    /* ─── TAB SWITCHING ─── */
    const tabs = document.querySelectorAll('.tab');
    const panels = document.querySelectorAll('.tab-panel');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            panels.forEach(p => p.classList.add('hidden'));
            tab.classList.add('active');
            document.getElementById('tab-' + tab.dataset.tab).classList.remove('hidden');
        });
    });

    /* ─────────────────────────────────────
       MANUAL TAB
    ───────────────────────────────────── */
    const analyzeBtn  = document.getElementById('analyzeBtn');
    const reviewInput = document.getElementById('reviewInput');
    const results     = document.getElementById('results');
    const charCount   = document.getElementById('charCount');
    const clearBtn    = document.getElementById('clearHistory');
    const historyList = document.getElementById('historyList');

    reviewInput.addEventListener('input', () => {
        const n = reviewInput.value.length;
        charCount.textContent = `${n} character${n !== 1 ? 's' : ''}`;
    });

    clearBtn.addEventListener('click', () => {
        historyList.innerHTML = '<li class="history-empty">No analyses yet. Run your first one above.</li>';
    });

    analyzeBtn.addEventListener('click', async () => {
        const text = reviewInput.value.trim();
        if (!text) return;

        analyzeBtn.disabled = true;
        document.getElementById('btnText').textContent = 'Analyzing…';
        results.classList.add('hidden');

        try {
            const res  = await fetch('/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text })
            });
            const data = await res.json();
            renderManualResults(data, text);
        } catch (err) {
            console.error(err);
        } finally {
            analyzeBtn.disabled = false;
            document.getElementById('btnText').textContent = 'Analyze';
        }
    });

    function renderManualResults(data, text) {
        setVerdict('tb',    data.textblob);
        setVerdict('vader', data.vader);
        setBar('pos', data.vader.details.pos);
        setBar('neu', data.vader.details.neu);
        setBar('neg', data.vader.details.neg);

        // Final verdict
        const finalEl  = document.getElementById('final-verdict');
        const scoreEl  = document.getElementById('final-score');
        const badgeEl  = document.getElementById('confidence-badge');

        finalEl.textContent = data.final;
        finalEl.className   = 'verdict-word verdict-word-final ' + data.final.toLowerCase();
        scoreEl.textContent = `Weighted score: ${data.final_score.toFixed(3)}`;

        const confClass = { High: 'conf-high', Medium: 'conf-medium', Low: 'conf-low' };
        badgeEl.textContent = data.confidence + ' Confidence';
        badgeEl.className   = 'confidence-badge ' + (confClass[data.confidence] || '');

        results.classList.remove('hidden');
        addHistory(text, data.final); // history uses final sentiment
    }

    function setVerdict(prefix, model) {
        const wordEl  = document.getElementById(`${prefix}-verdict`);
        const scoreEl = document.getElementById(`${prefix}-score`);
        wordEl.textContent  = model.sentiment;
        wordEl.className    = 'verdict-word ' + model.sentiment.toLowerCase();
        scoreEl.textContent = `Score: ${model.score.toFixed(3)}`;
    }

    function setBar(key, value) {
        document.getElementById(`bar-${key}`).style.width = `${(value * 100).toFixed(1)}%`;
        document.getElementById(`val-${key}`).textContent  = value.toFixed(2);
    }

    function addHistory(text, sentiment) {
        const empty = historyList.querySelector('.history-empty');
        if (empty) empty.remove();
        const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const li   = document.createElement('li');
        li.className = 'history-item';
        li.innerHTML = `
            <span class="h-text">${esc(text.slice(0, 80))}${text.length > 80 ? '…' : ''}</span>
            <span class="h-tag ${sentiment.toLowerCase()}">${sentiment}</span>
            <span class="h-time">${time}</span>
        `;
        historyList.prepend(li);
        const items = historyList.querySelectorAll('.history-item');
        if (items.length > 8) items[items.length - 1].remove();
    }

    /* ─────────────────────────────────────
       UPLOAD TAB
    ───────────────────────────────────── */
    const fileInput      = document.getElementById('fileInput');
    const dropZone       = document.getElementById('dropZone');
    const browseBtn      = document.getElementById('browseBtn');
    const filePreview    = document.getElementById('filePreview');
    const fileName       = document.getElementById('fileName');
    const fileSize       = document.getElementById('fileSize');
    const fileIcon       = document.getElementById('fileIcon');
    const removeFileBtn  = document.getElementById('removeFile');
    const columnWrapper  = document.getElementById('columnWrapper');
    const columnSelect   = document.getElementById('columnSelect');
    const uploadBtn      = document.getElementById('uploadBtn');
    const uploadStatus   = document.getElementById('uploadStatus');
    const bulkResults    = document.getElementById('bulkResults');

    let selectedFile = null;

    // Open file picker
    browseBtn.addEventListener('click', () => fileInput.click());
    dropZone.addEventListener('click', (e) => {
        if (e.target !== browseBtn) fileInput.click();
    });

    // Drag & drop
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length) handleFile(fileInput.files[0]);
    });

    removeFileBtn.addEventListener('click', () => {
        selectedFile = null;
        fileInput.value = '';
        filePreview.classList.add('hidden');
        dropZone.classList.remove('hidden');
        uploadBtn.disabled = true;
        bulkResults.classList.add('hidden');
        uploadStatus.textContent = '';
    });

    async function handleFile(file) {
        const ext = file.name.split('.').pop().toLowerCase();
        const allowed = ['csv', 'xlsx', 'xls', 'pdf'];
        if (!allowed.includes(ext)) {
            uploadStatus.textContent = 'Unsupported file type. Use CSV, Excel, or PDF.';
            uploadStatus.className   = 'upload-status error';
            return;
        }

        selectedFile = file;
        uploadStatus.textContent = '';
        uploadStatus.className   = 'upload-status';

        // Show preview card
        fileName.textContent = file.name;
        fileSize.textContent = formatBytes(file.size);
        fileIcon.textContent = ext.toUpperCase();
        dropZone.classList.add('hidden');
        filePreview.classList.remove('hidden');
        uploadBtn.disabled = false;

        // For CSV/Excel: fetch actual column names from server
        if (['csv', 'xlsx', 'xls'].includes(ext)) {
            columnWrapper.classList.remove('hidden');
            columnSelect.innerHTML = '<option value="">Loading columns…</option>';
            uploadStatus.textContent = 'Reading file columns…';

            try {
                const fd = new FormData();
                fd.append('file', file);
                const res  = await fetch('/preview', { method: 'POST', body: fd });
                const data = await res.json();

                if (data.error) throw new Error(data.error);

                // Populate dropdown with real column names
                columnSelect.innerHTML = '';
                data.columns.forEach(col => {
                    const opt       = document.createElement('option');
                    opt.value       = col;
                    opt.textContent = col;
                    if (col === data.suggested) opt.selected = true;
                    columnSelect.appendChild(opt);
                });

                // Show sample from suggested column
                const sample = data.sample.map(s => s.slice(0, 60)).join(' · ');
                uploadStatus.textContent = `Preview: "${sample}"`;
                uploadStatus.className   = 'upload-status';

            } catch (err) {
                columnSelect.innerHTML = '<option value="">— could not read columns —</option>';
                uploadStatus.textContent = 'Could not read columns: ' + err.message;
                uploadStatus.className   = 'upload-status error';
            }
        } else {
            // PDF — no column selector needed
            columnWrapper.classList.add('hidden');
            uploadStatus.textContent = 'PDF ready. Each line will be treated as a review.';
        }
    }

    uploadBtn.addEventListener('click', async () => {
        if (!selectedFile) return;

        uploadBtn.disabled = true;
        document.getElementById('uploadBtnText').textContent = 'Analyzing…';
        uploadStatus.textContent = 'Processing file…';
        uploadStatus.className   = 'upload-status';
        bulkResults.classList.add('hidden');

        try {
            const formData = new FormData();
            formData.append('file', selectedFile);
            // Always send the selected column — it's now populated from /preview
            const col = columnSelect.value.trim();
            formData.append('column', col);

            const res  = await fetch('/upload', { method: 'POST', body: formData });
            const data = await res.json();

            if (data.error) {
                uploadStatus.textContent = data.error;
                uploadStatus.className   = 'upload-status error';
                return;
            }

            renderBulkResults(data);
            uploadStatus.textContent = `${data.total} reviews analyzed successfully.`;

        } catch (err) {
            uploadStatus.textContent = 'An error occurred during analysis.';
            uploadStatus.className   = 'upload-status error';
            console.error(err);
        } finally {
            uploadBtn.disabled = false;
            document.getElementById('uploadBtnText').textContent = 'Analyze File';
        }
    });

    function renderBulkResults(data) {
        const { total, counts, results } = data;

        // Summary cards
        document.getElementById('sumTotal').textContent = total;
        document.getElementById('sumPos').textContent   = counts.Positive;
        document.getElementById('sumNeu').textContent   = counts.Neutral;
        document.getElementById('sumNeg').textContent   = counts.Negative;

        // Distribution bar
        const pct = (n) => total > 0 ? ((n / total) * 100).toFixed(1) + '%' : '0%';
        document.getElementById('dist-pos').style.width = pct(counts.Positive);
        document.getElementById('dist-neu').style.width = pct(counts.Neutral);
        document.getElementById('dist-neg').style.width = pct(counts.Negative);

        // Table
        const tbody = document.getElementById('bulkTableBody');
        tbody.innerHTML = '';
        results.forEach((row, i) => {
            const confClass = { High: 'conf-high', Medium: 'conf-medium', Low: 'conf-low' };
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${i + 1}</td>
                <td class="td-review">${esc(row.text)}</td>
                <td><span class="sentiment-badge badge-${row.textblob.sentiment.toLowerCase()}">${row.textblob.sentiment}</span></td>
                <td>${row.textblob.score.toFixed(3)}</td>
                <td><span class="sentiment-badge badge-${row.vader.sentiment.toLowerCase()}">${row.vader.sentiment}</span></td>
                <td>${row.vader.score.toFixed(3)}</td>
                <td><span class="sentiment-badge badge-${row.final.toLowerCase()}">${row.final}</span></td>
                <td><span class="confidence-badge ${confClass[row.confidence] || ''}">${row.confidence}</span></td>
            `;
            tbody.appendChild(tr);
        });

        bulkResults.classList.remove('hidden');
    }

    /* ─── HELPERS ─── */
    function formatBytes(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }

    function esc(str) {
        return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    }
});
