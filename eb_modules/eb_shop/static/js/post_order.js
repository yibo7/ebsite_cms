$(function () {

    $('#form_address').on('submit', function (e) {
      e.preventDefault(); // 阻止默认提交行为

      const prams = {};
        $(this).serializeArray().forEach(function(item) {
          prams[item.name] = item.value;
        });
      post_form("/api/add_address",prams,function(rz){
        if(rz.code===0){
            Refesh();
        }else{
            alert(rz.msg);
        }
    });
    });

  });

function del_address(data_id){
    if(!confirm("确定要删除地址吗?")){
        return;
    }
    const prams = {"data_id":data_id}
    post_form("/api/add_address",prams,function(rz){
        if(rz.code===0){
            Refesh();
        }else{
            alert(rz.msg);
        }
    });
}

function post_order(){
    address_id = get_radio_value("address");
    if(address_id)
    { 
      const form = document.getElementById('form_post');
      form.submit();
         
    }else{
        alert("请选择一个地址，如果没有先添加!");
    }
}