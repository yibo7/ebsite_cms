from bll.user_group import UserGroup
from model_controls.control_base import ControlBase


class ProductSku(ControlBase):

    def __init__(self):
        super().__init__()
        self.id: str = 'eb_shop_1'
        self.name: str = '商品规格'
        self.info: str = '商品规格实际上就是商品的SKU，往往每个SKU会对应着：市场价格，成本价，库存量，产品图片'
        # 模拟用户组数据，实际使用时会从数据库读取

        group = UserGroup().find_all()

        self.user_groups = [
            {'id': str(item._id), 'name': item.name}
            for item in (group or [])
        ]

    def get_control_temp(self, field_model: dict) -> str:
        show_name = field_model.get('show_name')
        name = field_model.get('name')

        # 将用户组数据转为JSON字符串
        import json
        user_groups_json = json.dumps(self.user_groups, ensure_ascii=False)


        temp = """
            <div id="app" >
    <h3>#show_name#</h3>

    <table class="table table-bordered align-middle">
      <thead>
        <tr>
          <th style="width: 120px;">规格图片</th>
          <th style="width: 33%;">规格名称</th>
          <th style="width: 100px;">市场价格</th>
          <th style="width: 100px;">成本价</th>
          <th style="width: 120px;">库存量</th>
          <th style="width: 150px;">货号</th>
          <th style="width: 100px;">重量(g)</th>
          <th style="width: 200px;">操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(spec, index) in specs" :key="index">
          <td @click="uploadImage(index,spec.image)" style="cursor:pointer;">
            <img :src="spec.image || placeholder" alt="规格图片" class="img-thumbnail" style="max-width: 100px; max-height: 100px;" />
           </td>
           <td>
            <input type="text" v-model="spec.name" class="form-control" />
           </td>
           <td>
            <input type="number" v-model.number="spec.marketPrice" class="form-control" min="0" step="0.01" />
           </td>
           <td>
            <input type="number" v-model.number="spec.costPrice" class="form-control" min="0" step="0.01" />
           </td>
           <td>
            <input type="number" v-model.number="spec.stock" class="form-control" min="0" step="1" />
           </td>
            <td><input type="text" v-model="spec.sku" class="form-control" /></td>
           <td><input type="number" v-model.number="spec.weight" class="form-control" min="0" step="0.01" /></td>
           <td>
             <div class="d-flex gap-1 flex-wrap">
             <button type="button" class="btn btn-outline-info btn-sm" @click="openGroupPriceModal(index)"><i class="fa fa-users"></i> 会员价</button>
             <button type="button" class="btn btn-outline-warning btn-sm" @click="openQtyPriceModal(index)"><i class="fa fa-layer-group"></i> 阶梯价</button>
             <button type="button" class="btn btn-outline-danger btn-sm" @click="deleteSpec(index)"><i class="fa fa-trash-o"></i> 删除</button>
             </div>
           </td>
         </tr>
         <tr>
           <td>
           </td>
           <td>
            <input type="text" v-model="newSpec.name" placeholder="规格名称" class="form-control" />
           </td>
           <td>
            <input type="number" v-model.number="newSpec.marketPrice" placeholder="市场价格" class="form-control" min="0" step="0.01" />
           </td>
           <td>
            <input type="number" v-model.number="newSpec.costPrice" placeholder="成本价" class="form-control" min="0" step="0.01" />
           </td>
           <td>
            <input type="number" v-model.number="newSpec.stock" placeholder="库存量" class="form-control" min="0" step="1" />
           </td>
            <td><input type="text" v-model="newSpec.sku" placeholder="货号" class="form-control" /></td>
           <td><input type="number" v-model.number="newSpec.weight" placeholder="重量" class="form-control" min="0" step="0.01" /></td>
           <td>
            <button type="button" class="btn btn-primary btn-sm" @click="addSpec"><i class="fa fa-plus"></i> 添加</button>
           </td>
          </tr>
       </tbody>
    </table>

    <!-- 隐藏 input 用于提交 -->
    <input type="hidden" name="#field_name#" value='[[model.#field_name# | tojson ]]' ref="skuInput" />

    <!-- 用户组价格设置模态框 -->
    <div class="modal fade" id="groupPriceModal" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">设置用户组价格 - ${ currentSpecName }</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body">
            <table class="table table-bordered">
              <thead>
                <tr>
                  <th>用户组</th>
                  <th>价格</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(group, idx) in groupPricesList" :key="group.id">
                  <td>${ group.name }</td>
                  <td>
                    <input type="number" v-model.number="group.price" class="form-control" min="0" step="0.01" placeholder="请输入价格" />
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
            <button type="button" class="btn btn-primary" @click="saveGroupPrices">保存</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 阶梯价设置模态框 -->
    <div class="modal fade" id="qtyPriceModal" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">设置阶梯价 - ${ currentSpecName }</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body">
            <p class="text-muted small mb-3">设置不同采购数量区间的批发价格。未在任何区间的采购量将以其他价格规则为准。</p>
            <table class="table table-bordered">
              <thead>
                <tr>
                  <th style="width:100px;">最小数量</th>
                  <th style="width:100px;">最大数量</th>
                  <th style="width:100px;">价格</th>
                  <th style="width:60px;">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(tier, idx) in qtyPricesList" :key="idx">
                  <td>
                    <input type="number" v-model.number="tier.min_qty" class="form-control" min="1" step="1" placeholder="最小" />
                  </td>
                  <td>
                    <input type="number" v-model.number="tier.max_qty" class="form-control" min="0" step="1" placeholder="最大(留空不限)" />
                  </td>
                  <td>
                    <input type="number" v-model.number="tier.price" class="form-control" min="0" step="0.01" placeholder="价格" />
                  </td>
                  <td class="text-center">
                    <button type="button" class="btn btn-outline-danger btn-sm" @click="deleteQtyPrice(idx)" title="删除此行">
                      <i class="fa fa-trash-o"></i>
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
            <button type="button" class="btn btn-outline-primary btn-sm" @click="addQtyPriceRow">
              <i class="fa fa-plus"></i> 添加阶梯
            </button>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
            <button type="button" class="btn btn-primary" @click="saveQtyPrices">保存</button>
          </div>
        </div>
      </div>
    </div>

  </div>

  <script src="https://cdn.jsdelivr.net/npm/vue@2.4.1/dist/vue.js"></script> 

  <script>
   const userGroupsData = #user_groups_json#;

   const vm = new Vue({
      el: '#app',
      delimiters: ['${', '}'],
      data() {
        return {
          specs: [],
          newSpec: {
            name: '',
            image: '/nopic.gif',
            marketPrice: 0.0,
            costPrice: 0.0,
            stock: 0,
            sku: '',
            weight: 0.0,
            group_prices: [],
            group_qty_prices: []
          },
          placeholder: '/nopic.gif',
          currentSpecIndex: -1,
          currentSpecName: '',
          // 会员价
          groupPricesList: [],
          groupModalInstance: null,
          // 阶梯价
          qtyPricesList: [],
          qtyModalInstance: null
        };
      },
      mounted() {
        try {
          let initSkuData = this.$refs.skuInput.value;
          if (initSkuData) {
            const parsed = JSON.parse(initSkuData);
            if (Array.isArray(parsed)) {
              this.specs = parsed;
              this.specs.forEach(spec => {
                if (!spec.group_prices) {
                  spec.group_prices = [];
                }
                if (!spec.group_qty_prices) {
                  spec.group_qty_prices = [];
                }
              });
            }
          }
        } catch (e) {
          console.warn('初始化 SKU 数据失败：', e);
        }

        const groupModalElement = document.getElementById('groupPriceModal');
        if (groupModalElement) {
          this.groupModalInstance = new bootstrap.Modal(groupModalElement);
        }
        const qtyModalElement = document.getElementById('qtyPriceModal');
        if (qtyModalElement) {
          this.qtyModalInstance = new bootstrap.Modal(qtyModalElement);
        }
      },
      watch: {
        specs: {
          handler(newVal) {
            this.$refs.skuInput.value = JSON.stringify(newVal);
          },
          deep: true
        }
      },
      methods: {
        addSpec() {
          if (!this.newSpec.name || !this.newSpec.sku) {
            alert('规格名称与货号不能为空!');
            return;
          };

          const isSkuDuplicate = this.specs.some(spec => spec.sku === this.newSpec.sku);
          if (isSkuDuplicate) {
            alert('不允许有相同的货号（SKU）！');
            return;  
          }

          const newSpecData = { ...this.newSpec };
          if (!newSpecData.group_prices) {
            newSpecData.group_prices = [];
          }
          if (!newSpecData.group_qty_prices) {
            newSpecData.group_qty_prices = [];
          }

          this.specs.push(newSpecData);
          this.newSpec = {
            name: '', image: '/nopic.gif', marketPrice: null, costPrice: null, 
            stock: null, sku: '', weight: null, group_prices: [], group_qty_prices: []
          };
        },
        deleteSpec(index) {
          if (confirm('确定要删除该规格吗？')) {
            this.specs.splice(index, 1);
          }
        },
        uploadImage(index, src) {
            OpenUploadImg(index, src);
        },
        // ── 会员价 ──
        openGroupPriceModal(index) {
          this.currentSpecIndex = index;
          const spec = this.specs[index];
          this.currentSpecName = spec.name || '未命名规格';

          if (!spec.group_prices) {
            spec.group_prices = [];
          }

          this.groupPricesList = userGroupsData.map(group => {
            const existingPrice = spec.group_prices.find(gp => gp.group_id === group.id);
            return {
              id: group.id,
              name: group.name,
              price: existingPrice ? existingPrice.price : null
            };
          });

          if (this.groupModalInstance) {
            this.groupModalInstance.show();
          }
        },
        saveGroupPrices() {
          const validPrices = this.groupPricesList.filter(item => item.price !== null && item.price !== '');

          const groupPricesToSave = validPrices.map(item => ({
            group_id: item.id,
            group_name: item.name,
            price: parseFloat(item.price)
          }));

          if (this.currentSpecIndex !== -1 && this.specs[this.currentSpecIndex]) {
            this.$set(this.specs[this.currentSpecIndex], 'group_prices', groupPricesToSave);
          }

          if (this.groupModalInstance) {
            this.groupModalInstance.hide();
          }
        },
        // ── 阶梯价 ──
        openQtyPriceModal(index) {
          this.currentSpecIndex = index;
          const spec = this.specs[index];
          this.currentSpecName = spec.name || '未命名规格';

          if (!spec.group_qty_prices) {
            spec.group_qty_prices = [];
          }

          // 深拷贝当前阶梯价数据到编辑列表（与会员价保持一致的初始化方式）
          this.qtyPricesList = spec.group_qty_prices.map(tier => ({
            min_qty: tier.min_qty,
            max_qty: tier.max_qty,
            price: tier.price
          }));

          if (this.qtyModalInstance) {
            this.qtyModalInstance.show();
          }
        },
        addQtyPriceRow() {
          this.qtyPricesList.push({
            min_qty: null,
            max_qty: null,
            price: null
          });
        },
        deleteQtyPrice(idx) {
          this.qtyPricesList.splice(idx, 1);
        },
        // 参考会员价 saveGroupPrices 的简洁模式重构
        saveQtyPrices() {
          // 过滤掉无效行（与会员价一样只做基本的 null/'' 过滤）
          const validTiers = this.qtyPricesList.filter(
            tier => tier.min_qty !== null && tier.min_qty !== '' && tier.price !== null && tier.price !== ''
          );

          // 直接映射保存，不做 parseInt 转换（会员价也只做 parseFloat，保持数据原始类型）
          const qtyPricesToSave = validTiers.map(tier => ({
            min_qty: tier.min_qty,
            max_qty: (tier.max_qty !== null && tier.max_qty !== '') ? tier.max_qty : null,
            price: parseFloat(tier.price)
          }));

          // 与会员价一样：始终执行 $set，不提前返回，空数组也保存
          if (this.currentSpecIndex !== -1 && this.specs[this.currentSpecIndex]) {
            this.$set(this.specs[this.currentSpecIndex], 'group_qty_prices', qtyPricesToSave);
          }

          if (this.qtyModalInstance) {
            this.qtyModalInstance.hide();
          }
        }
      }
    });
    window.vm = vm;
    let current_index = 0;
    function OnConfirmImg(img_url) {
        if (window.vm && window.vm.specs && window.vm.specs[current_index]) {
          window.vm.$set(window.vm.specs[current_index], 'image', img_url);
        } else {
          console.warn("Vue 实例未准备好或索引无效");
        }
        $('#ebiframewin').modal('hide');
    }
    function OpenUploadImg(index, src) {
        current_index = index;
        let sUrl = "/admin/upload_img?src=" + src;
        OpenIframe(sUrl, "上传图片", btnText = "确认", height = 600, width = 800);
    }
  </script>
        """

        temp = temp.replace("#field_name#", name)
        temp = temp.replace("#show_name#", show_name)
        temp = temp.replace("#user_groups_json#", user_groups_json)

        return temp