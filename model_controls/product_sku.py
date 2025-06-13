from model_controls.control_base import ControlBase


class ProductSku(ControlBase):

    def __init__(self):
        super().__init__()
        self.id: int = 10
        self.name: str = '商品规格'
        self.info: str = '商品规格实际上就是商品的SKU，往往每个SKU会对应着：市场价格，成本价，库存量，产品图片'

    def get_control_temp(self, field_model: dict) -> str:
        show_name = field_model.get('show_name')
        name = field_model.get('name')
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
          <th style="width: 120px;">操作</th>
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
    <input type="hidden" name="#field_name#" value="[[model.#field_name#]]" ref="skuInput" />

  </div>

  <script src="https://cdn.jsdelivr.net/npm/vue@2.4.1/dist/vue.js"></script>
  <script>
    
   const vm = new Vue({
      el: '#app',
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
            weight: 0.0
          },
          placeholder: '/nopic.gif',
        };
      },
      mounted() {
        try {
          let initSkuData = this.$refs.skuInput.value;
          if (initSkuData) {
            const parsed = JSON.parse(initSkuData);
            if (Array.isArray(parsed)) {
              this.specs = parsed;
            }
          }
           
        } catch (e) {
          console.warn('初始化 SKU 数据失败：', e);
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
          // 简单校验
          if (!this.newSpec.name) {
            alert('请填写规格名称');
            return;
          }
          this.specs.push({ ...this.newSpec });
          // 清空新增表单
          this.newSpec = {
            name: '', image: '', marketPrice: null, costPrice: null, stock: null, sku: '', weight: null
          };
        },
        deleteSpec(index) {
          this.specs.splice(index, 1);
        },
        uploadImage(index,src) {
            OpenUploadImg(index,src)
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

        temp = temp.replace("#field_name#",name)
        temp = temp.replace("#show_name#", show_name)

        return temp