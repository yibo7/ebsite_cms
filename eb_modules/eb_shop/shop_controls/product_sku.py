from bll.user_group import UserGroup
from model_controls.control_base import ControlBase


class ProductSku(ControlBase):

    def __init__(self):
        super().__init__()
        self.id: int = 10
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
          <th>规格名称</th>
          <th style="width: 120px;">市场价格</th>
          <th style="width: 120px;">成本价</th>
          <th style="width: 120px;">库存量</th>
          <th style="width: 200px;">货号</th>
          <th style="width: 120px;">重量(g)</th>
          <th style="width: 180px;">操作</th>
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
            <button type="button" class="btn btn-info btn-sm me-1" @click="openGroupPriceModal(index)">设置用户组价格</button>
            <button type="button" class="btn btn-danger btn-sm" @click="deleteSpec(index)">删除</button>
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
            <button type="button" class="btn btn-primary btn-sm" @click="addSpec">添加</button>
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
            group_prices: []
          },
          placeholder: '/nopic.gif',
          currentSpecIndex: -1,
          currentSpecName: '',
          groupPricesList: [],
          modalInstance: null
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
              });
            }
          }
        } catch (e) {
          console.warn('初始化 SKU 数据失败：', e);
        }

        const modalElement = document.getElementById('groupPriceModal');
        if (modalElement) {
          this.modalInstance = new bootstrap.Modal(modalElement);
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

          this.specs.push(newSpecData);
          this.newSpec = {
            name: '', image: '/nopic.gif', marketPrice: null, costPrice: null, 
            stock: null, sku: '', weight: null, group_prices: []
          };
        },
        deleteSpec(index) {
          this.specs.splice(index, 1);
        },
        uploadImage(index, src) {
            OpenUploadImg(index, src);
        },
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

          if (this.modalInstance) {
            this.modalInstance.show();
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

          if (this.modalInstance) {
            this.modalInstance.hide();
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