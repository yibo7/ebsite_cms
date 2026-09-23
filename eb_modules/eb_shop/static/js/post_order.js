$(function () {

    // ============================================================
    // 新增地址表单展开/收起
    // ============================================================
    $('#btnToggleAddrForm').on('click', function () {
        var $form = $('#newAddrForm');
        if ($form.is(':visible')) {
            $form.slideUp(180);
        } else {
            resetAddrForm();
            $form.slideDown(180);
        }
    });

    // ============================================================
    // 地址选择切换高亮
    // ============================================================
    $(document).on('click touchstart', '.address-item', function (e) {
        // 跳过编辑/删除按钮点击
        if ($(e.target).closest('.btn-edit-addr, .btn-del-addr').length) return;
        var radio = $(this).find('input[type="radio"]');
        radio.prop('checked', true);
        $('.address-item').removeClass('active');
        $(this).addClass('active');
    });

    // 页面加载时默认选中第一项
    var firstChecked = $('.address-item input[type="radio"]:checked');
    if (firstChecked.length) {
        firstChecked.closest('.address-item').addClass('active');
    }

    // ============================================================
    // 编辑地址 — 点击铅笔图标
    // ============================================================
    $(document).on('click', '.btn-edit-addr', function () {
        var $item = $(this).closest('.address-item');
        var addrId = $item.data('addr-id');
        var name = $item.data('name');
        var phone = $item.data('phone');
        var email = $item.data('email') || '';
        var postcode = $item.data('postcode') || '';
        var address = $item.data('address') || '';

        // 填充地址表单
        $('#editAddrId').val(addrId);
        $('#form_address input[name="user_name"]').val(name);
        $('#form_address input[name="phone"]').val(phone);
        $('#form_address input[name="email"]').val(email);
        $('#form_address input[name="post_code"]').val(postcode);
        $('#form_address input[name="address_info"]').val(address);

        // 更新保存按钮文字
        $('#form_address .btn-save-address-text').text('保存修改');

        // 展开表单
        var $form = $('#newAddrForm');
        if (!$form.is(':visible')) {
            $form.slideDown(180);
        }
    });

    // ============================================================
    // 重置地址表单
    // ============================================================
    function resetAddrForm() {
        $('#editAddrId').val('');
        $('#form_address')[0].reset();
        $('#form_address .btn-save-address-text').text('保存地址');
    }

    // ============================================================
    // 新增 / 修改地址
    // ============================================================
    $('#form_address').on('submit', function (e) {
        e.preventDefault();

        var prams = {};
        $(this).serializeArray().forEach(function (item) {
            prams[item.name] = item.value;
        });

        // 编辑模式：带上 data_id
        var editId = $('#editAddrId').val();
        if (editId) {
            prams['data_id'] = editId;
        }

        post_form("/api/add_address", prams, function (rz) {
            if (rz.code === 0) {
                Refesh();
            } else {
                alert(rz.msg);
            }
        });
    });

    // ============================================================
    // 删除地址
    // ============================================================
    window.del_address = function (data_id) {
        if (!confirm("确定要删除地址吗?")) return;
        post_form("/api/add_address", { data_id: data_id }, function (rz) {
            if (rz.code === 0) {
                Refesh();
            } else {
                alert(rz.msg);
            }
        });
    };

    // ============================================================
    // 提交订单
    // ============================================================
    window.post_order = function () {
        var addressChecked = $('input[name="address"]:checked').val();
        if (!addressChecked) {
            alert("请选择一个收货地址，如果没有请先添加");
            return;
        }

        // 将备注写入隐藏字段
        var remark = $('#remarkText').val() || '';
        $('#remarkField').val(remark);

        // 提交表单
        var form = document.getElementById('form_post');
        form.submit();
    };

});