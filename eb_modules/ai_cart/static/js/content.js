
/* ===== 加入询价篮 ===== */
function addToQuoteBasket(id, title, pic, price, url) {
  var qtyEl = document.querySelector('.qty-control input[type=number]');
  var qty = qtyEl ? parseInt(qtyEl.value) || 1 : 1;
  var items = [];
  try { var saved = localStorage.getItem('eb_quote_items'); if (saved) items = JSON.parse(saved) || []; } catch(e) {}
  var existing = items.find(function(i) { return i.id === id; });
  if (existing) { existing.qty += qty; } else {
    var selSku = '', selMp = 0;
    if (typeof SelProduct !== 'undefined' && SelProduct) { selSku = SelProduct.sku || ''; selMp = parseFloat(SelProduct.marketPrice) || 0; }
    items.push({ id:id, name:title, unit_price:price, market_price:selMp||price, qty:qty, class_name:'打印耗材', sku:selSku||id, url:url || '/a'+(window.contentId||id)+'.html', remarks:'', small_pic:pic||'', icon:pic||'🖨️' });
  }
  localStorage.setItem('eb_quote_items', JSON.stringify(items));
  var badges = document.querySelectorAll('.cart-badge');
  var total = items.reduce(function(s,i){return s+(i.qty||1);},0);
  for (var i=0;i<badges.length;i++){if(total>0){badges[i].textContent=total;badges[i].classList.remove('hidden');}else{badges[i].classList.add('hidden');}}
  var t=document.getElementById('toast-message'),s=document.getElementById('toast-text');
  if(t&&s){s.textContent='已加入询价篮';t.classList.add('show');setTimeout(function(){t.classList.remove('show');},2000);}
}
