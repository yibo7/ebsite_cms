document.addEventListener('DOMContentLoaded', function () {
  const form = document.querySelector('#search form');
  const input = document.querySelector('#search-text');
  const radios = document.querySelectorAll('.search-type input[name="type"]');

  function updateFormAndSubmit(e) {
    e.preventDefault(); // 阻止默认提交
    const keyword = input.value.trim();
    if (!keyword) return; // 关键词为空则不执行

    const selected = document.querySelector('.search-type input[name="type"]:checked').id;

    let action = '';
    let paramName = '';

    switch (selected) {
      case 'type-zhannei':
        action = '/search.html';
        paramName = 'k';
        break;
      case 'type-baidu':
        action = 'https://www.baidu.com/s';
        paramName = 'wd';
        break;
      case 'type-google':
        action = 'https://www.google.com/search';
        paramName = 'q';
        break;
      case 'type-bing':
        action = 'https://www.bing.com/search';
        paramName = 'q';
        break;
    }

    // 构造最终 URL 并跳转
    const searchUrl = `${action}?${paramName}=` + encodeURIComponent(keyword);
    window.open(searchUrl, '_blank');
  }

  // 点击按钮或按回车都触发搜索
  form.addEventListener('submit', updateFormAndSubmit);
});