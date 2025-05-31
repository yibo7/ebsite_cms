$(function($) {

  changDarkWhile(); // 保留暗/亮模式切换，因为它不直接冲突菜单

  gotoUpInit(); // 保留回到顶部功能

  lefeMenuScrollToLab(); // 保留菜单滚动到描点功能

  $('#mini-button').on('click', function() {
    if (!$('.sidebar-nav').hasClass()) { // 检查 sidebar-nav 是否有其他类，这行可能有逻辑问题
      $('body').addClass('animate-nav');
    }
    trigger_lsm_mini();
  });

  $("#sidebar-switch").on("click", function () {
      $("#offcanvas-menus").html($("#pc-menus").html());
      const myOffcanvasEl = document.getElementById('myOffcanvas');
      const bsOffcanvas = new bootstrap.Offcanvas(myOffcanvasEl);
      bsOffcanvas.show();
  });

});


// ==== 函数定义 ====

// 滚动到页面顶部的设置，保留
function gotoUpInit() {
  $(window).scroll(function() {
    if ($(this).scrollTop() >= 50) {
      $('#go-to-up').fadeIn(200);
      $('.big-header-banner').addClass('header-bg'); // 如果模板中没有 .big-header-banner 请注意
    } else {
      $('#go-to-up').fadeOut(200);
      $('.big-header-banner').removeClass('header-bg');
    }
  });
  $('.go-up').click(function() {
    $('body,html').animate({
      scrollTop: 0
    }, 500);
    return false;
  });
}

// Cookie 设置函数，保留（被 changDarkWhile 调用）
function setCookie(t, e, a) {
  var i = "";
  if ("" != a) {
    var o = new Date();
    o.setTime(o.getTime() + 24 * a * 60 * 60 * 1e3);
    (i = "expires=" + o.toGMTString());
  }
  document.cookie = t + "=" + e + "; " + i + "; path=/";
}

// 日间模式和夜间模式的切换，保留
function changDarkWhile() {
  var default_c = "io-white-mode";
  var night = document.cookie.replace(/(?:(?:^|.*;\s*)io_night_mode\s*\=\s*([^;]*).*$)|^.*$/, "$1");
  try {
    if (night === "0") {
      document.documentElement.classList.add("io-black-mode");
      document.documentElement.classList.remove(default_c);
    } else {
      document.documentElement.classList.remove("io-black-mode");
      document.documentElement.classList.add(default_c);
    }
  } catch (_) {};

  $(document).on("click", ".switch-dark-mode", function(e) {
    e.preventDefault();
    $("html").toggleClass("io-black-mode");
    toggleDarkMode(true);
    $("#" + $(".switch-dark-mode").attr("aria-describedby")).remove();
  });

  function toggleDarkMode(set_cookie) {
    const htmlElement = $("html");
    const switchButton = $(".switch-dark-mode");
    const modeIcon = $(".mode-ico");
    // const postContentBody = $("#post_content_ifr").contents().find("body"); // 检查这个元素是否存在于你的模板中

    const isDarkMode = htmlElement.hasClass("io-black-mode");

    if (isDarkMode) {
      // if(postContentBody.length) postContentBody.addClass("io-black-mode"); // 仅当元素存在时操作

      if (set_cookie) {
        setCookie("io_night_mode", 0, 30);
      }

      updateSwitchButtonText(switchButton, "白天模式");
      updateModeIcon(modeIcon, "fa-lightbulb-o", "fa-moon-o");

    } else {
      // if(postContentBody.length) postContentBody.removeClass("io-black-mode"); // 仅当元素存在时操作

      if (set_cookie) {
        setCookie("io_night_mode", 1, 30);
      }

      updateSwitchButtonText(switchButton, "夜间模式");
      updateModeIcon(modeIcon, "fa-moon-o", "fa-lightbulb-o");

    }

  }

  function updateSwitchButtonText(button, text) {
    if (button.attr("data-original-title")) {
      button.attr("data-original-title", text);
    } else {
      button.attr("title", text);
    }
  }

  function updateModeIcon(icon, addClass, removeClass) {
    icon.removeClass(removeClass).addClass(addClass);
  }

}


// // 左则菜单最大化或最小化
function trigger_lsm_mini() {
  if ($('.header-mini-btn input[type="checkbox"]').prop("checked")) {
      $('body').removeClass('mini-sidebar');
  } else {
      $('.sidebar-item.sidebar-show').removeClass('sidebar-show'); // 移除打开状态的sidebar-show类
      $('body').addClass('mini-sidebar');
  }
}

/*
点击左侧菜单定位scroll-target到描点
* */
function lefeMenuScrollToLab() {
  const offset = 90;

  // 页面加载时如果有 hash，则滚动到对应元素
  // if (window.location.hash) {
  //   const $scrollToElement = $(window.location.hash);
  //   if ($scrollToElement.length) {
  //     $("html, body").animate({
  //       scrollTop: $scrollToElement.offset().top - offset
  //     }, 1000);
  //   }
  // }

  // 菜单点击事件处理
  $(document).on('click', '.sidebar-menu .nav-item > .nav-link', function (ev) {
    const _this = $(this);
    const scrollTargetId = _this.data('scroll-target') || _this.attr('href');
    const isHashLink = scrollTargetId && scrollTargetId.startsWith('#');
    const isHomePage = location.pathname === '/' || location.pathname === '/index.html';
    const fallbackUrl = _this.data('link'); // 备用跳转链接

    if (isHashLink) {
      ev.preventDefault();

      if (isHomePage) {
        const $scrollToElement = $(scrollTargetId);
        if ($scrollToElement.length) {
          $("html, body").animate({
            scrollTop: $scrollToElement.offset().top - offset
          }, 500);
        } else if (fallbackUrl) {
          window.location.href = fallbackUrl + scrollTargetId;
        }
      } else {
        // 不在首页时直接跳转（使用 fallbackUrl 优先）
        if (fallbackUrl) {
            window.location.href = fallbackUrl
          // window.location.href = fallbackUrl + scrollTargetId;
        }
        // else {
        //   window.location.href = '/' + scrollTargetId;
        // }
      }
    }
  });
}

function ChkSo(ob) {

    if (ob.k.value == "") {
        alert("请输入要搜索的关键词");
        return false;
    }
}

/**
 * 基于boostrap5的吐丝
 * @param {any} sText
 * @param {any} time
 * @param {any} sTitle
 */
function Toast(sText, time = 5, sTitle = "提示") {
    var sbHtml = new StringBuilder();
        sbHtml.Append("<div class=\"bootstrap-toast position-fixed bottom-0 end-0 p-3\" style=\"z-index: 1000; \">");
        sbHtml.Append("    <div id=\"liveToast\" class=\"toast \" role=\"alert\" aria-live=\"assertive\" data-bs-delay=\"{0}\" aria-atomic=\"true\">");
        sbHtml.Append("        <div class=\"toast-header\">");
        sbHtml.Append("            <i style=\"color:#ff6a00\" class=\"fa fa-bell-o \"></i>&nbsp;&nbsp;");
        sbHtml.Append("            <strong class=\"me-auto\">{1}</strong>");
        sbHtml.Append("            <small>message</small>");
        sbHtml.Append("            <button type=\"button\" class=\"btn-close\" data-bs-dismiss=\"toast\" aria-label=\"Close\"></button>");
        sbHtml.Append("        </div>");
        sbHtml.Append("        <div class=\"toast-body\">");
        sbHtml.Append("            {2}");
        sbHtml.Append("        </div>");
        sbHtml.Append("    </div>");
        sbHtml.Append("</div>");
        let time_span = time * 1000;
        var sHtml = sbHtml.toString().format(time_span, sTitle, sText);

        var ob = $(".bootstrap-toast");

        if (ob.html() == null) {
            ob = $(sHtml).appendTo('body');
        }

        var myAlert = document.getElementById('liveToast');
        var bsAlert = new bootstrap.Toast(myAlert);
        bsAlert.show();

}
