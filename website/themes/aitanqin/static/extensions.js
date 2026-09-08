// ===== 动态生成波形条 =====
  // 每个卡片中的 .js-wave 容器自动生成 32 条波形
  // 每条高度在 6px ~ 22px 之间随机，模拟真实音频波形
  document.querySelectorAll('.js-wave').forEach(function(el) {
    var count = 32;
    for (var i = 0; i < count; i++) {
      var bar = document.createElement('i');
      // 随机高度 6~22px
      var height = 6 + Math.floor(Math.random() * 17);
      bar.style.height = height + 'px';
      el.appendChild(bar);
    }
  });

  // 根据 value 值渲染难度星级
function renderStars() {
   // 用 class 选择所有难度容器（避免 HTML 中重复 id 的问题）
   const containers = document.querySelectorAll('.level-value');
   if (!containers.length) return;

   containers.forEach(function (container) {
       const value = parseInt(container.getAttribute('value')) || 0;
       const total = 3;

       // 清空容器
       container.innerHTML = '';

       // 生成 span
       for (let i = 0; i < total; i++) {
           const span = document.createElement('span');
           if (i < value) {
               span.className = 'on';
           }
           container.appendChild(span);
       }
   });
}

// 页面加载后执行
renderStars();

// 自动选中主导航菜单（基于cid匹配）
if(cid){
    const currentCid = cid; // 或者直接用 cid 变量
    document.querySelectorAll('.navbar-nav .nav-link').forEach(el => {
      const itemCid = el.getAttribute('cid');
      if (itemCid == currentCid) {
        el.classList.add('active');
      }
    });

}


