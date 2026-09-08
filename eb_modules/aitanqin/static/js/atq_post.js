/**
 * 爱弹琴 - 乐谱发布页面前端逻辑
 * 处理文件哈希计算、重复检测、上传与表单提交
 */
(function () {
  'use strict';

  const UPLOAD_URL = '/atq/api/upload_score';
  const CHECK_HASH_URL = '/atq/api/check_score_hash';

  // DOM 元素
  const form = document.getElementById('scoreForm');
  const fileInput = document.getElementById('scoreFile');
  const uploadBtn = document.getElementById('uploadBtn');
  const uploadStatus = document.getElementById('uploadStatus');
  const fileInfo = document.getElementById('fileInfo');
  const fileNameDisplay = document.getElementById('fileNameDisplay');
  const scoreFilePath = document.getElementById('scoreFilePath');
  const scoreFileHash = document.getElementById('scoreFileHash');
  const submitBtn = document.getElementById('submitBtn');

  // 分类相关元素
  const classSelect = document.getElementById('classSelect');
  const classId = document.getElementById('classId');
  const classNId = document.getElementById('classNId');
  const className = document.getElementById('className');

  // 当前文件的哈希值（上传成功后保留）
  let currentFileHash = '';

  /** 显示上传状态信息 */
  function showStatus(msg, isError) {
    uploadStatus.style.display = 'block';
    uploadStatus.className = 'mt-2 alert alert-' + (isError ? 'danger' : 'info') + ' py-2 small';
    uploadStatus.textContent = msg;
  }

  /** 隐藏上传状态 */
  function hideStatus() {
    uploadStatus.style.display = 'none';
  }

  /** 显示已上传文件信息 */
  function showFileInfo(name) {
    fileNameDisplay.textContent = name;
    fileInfo.style.display = 'block';
  }

  /** 隐藏已上传文件信息 */
  function hideFileInfo() {
    fileInfo.style.display = 'none';
    fileNameDisplay.textContent = '';
  }

  /** 重置上传状态（用户重新选择文件时） */
  function resetUploadState() {
    hideStatus();
    hideFileInfo();
    scoreFilePath.value = '';
    scoreFileHash.value = '';
    currentFileHash = '';
  }

  // ===== 计算文件 SHA-256 哈希 =====
  async function computeFileHash(file) {
    const arrayBuffer = await file.arrayBuffer();
    const hashBuffer = await crypto.subtle.digest('SHA-256', arrayBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  }

  // ===== 检查哈希是否已存在 =====
  async function checkHashExists(hash) {
    const resp = await fetch(CHECK_HASH_URL + '?hash=' + encodeURIComponent(hash));
    const result = await resp.json();
    if (result.code !== 0) {
      throw new Error(result.msg || '查重失败');
    }
    return result.data.exists;
  }

  /** 上传文件到服务器 */
  async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);

    const resp = await fetch(UPLOAD_URL, {
      method: 'POST',
      body: formData
    });

    const result = await resp.json();

    if (result.code !== 0) {
      throw new Error(result.msg || '上传失败');
    }

    return result.data; // 返回文件路径，如 /scores/new/xxx.gp
  }

  // ===== 上传按钮点击事件 =====
  uploadBtn.addEventListener('click', async function () {
    const file = fileInput.files[0];
    if (!file) {
      showStatus('请先选择文件', true);
      return;
    }

    // 验证文件扩展名
    const ext = file.name.split('.').pop().toLowerCase();
    if (ext !== 'gp' && ext !== 'musicxml') {
      showStatus('不支持的文件格式，仅支持 .gp 和 .musicxml', true);
      fileInput.value = '';
      return;
    }

    // 禁用上传按钮防止重复点击
    uploadBtn.disabled = true;
    uploadBtn.textContent = '⏳ 计算哈希...';
    hideStatus();

    try {
      // 第一步：计算文件哈希
      const fileHash = await computeFileHash(file);
      currentFileHash = fileHash;

      // 第二步：查重
      uploadBtn.textContent = '⏳ 查重中...';
      const exists = await checkHashExists(fileHash);
      if (exists) {
        alert('该乐谱已存在，请勿重复上传');
        resetUploadState();
        uploadBtn.disabled = false;
        uploadBtn.textContent = '📤 上传';
        return;
      }

      // 第三步：上传文件
      uploadBtn.textContent = '⏳ 上传中...';
      const filePath = await uploadFile(file);
      scoreFilePath.value = filePath;
      scoreFileHash.value = fileHash;
      showFileInfo(file.name);
      showStatus('✅ 上传成功', false);
    } catch (err) {
      showStatus('❌ ' + (err.message || '操作失败，请重试'), true);
      resetUploadState();
    } finally {
      uploadBtn.disabled = false;
      uploadBtn.textContent = '📤 上传';
    }
  });

  // ===== 重新选择文件时重置状态 =====
  fileInput.addEventListener('change', function () {
    resetUploadState();
  });

  // ===== 分类选择 → 更新隐藏字段 =====
  classSelect.addEventListener('change', function () {
    const opt = this.options[this.selectedIndex];
    classId.value = opt.value;
    classNId.value = opt.getAttribute('data-cnid') || '';
    className.value = opt.getAttribute('data-cname') || '';
  });

  // ===== 表单提交验证 =====
  form.addEventListener('submit', function (e) {
    // 检查文件是否已上传（column_5 隐藏字段是否有值）
    if (!scoreFilePath.value) {
      e.preventDefault();
      alert('请先上传乐谱文件');
      return;
    }

    // 让浏览器原生 HTML5 验证执行
    if (!form.checkValidity()) {
      e.preventDefault();
      e.stopPropagation();
      form.classList.add('was-validated');
      return;
    }

    // 提交时禁用按钮防止重复提交
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status"></span> 提交中...';
  });

})();