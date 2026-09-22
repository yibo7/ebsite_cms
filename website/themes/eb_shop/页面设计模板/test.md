我现在需要将【产品信息.json】中的数据导入到NewsContent表中，导入字段映射如下：

| 产品信息.json字段 | NewsContent字段 |
| :--- | :--- |
| product_ename | title |
| brand | column_3 |
| model | column_4 |
| seo_keyword | seo_keyword |
| seo_description | seo_description |
| suitable_for | column_5 | 
| specs中第1个SKU spec_img的值 | small_pic |
| specs中第1个SKU market_price的值 | column_11 |
| specs | column_10 |

specs 应该编写为json格式定如column_10,
以【产品信息.json】的某条产品的spes为例子：
``` json
"specs": [
      {
        "model_cn": "原色/绿色",
        "color": "Green/OEM",
        "life_span": "5000OPage",
        "cost": 14,
        "svip": 16,
        "vip": 18,
        "market_price": 20,
        "code": "GX-IR1730-001",
        "spec_cname": "原色/绿色 约可复印5000O页。",
        "spec_ename": "Original / Green · Approx. 5,000 pages.",
        "spec_img": "/products/gx-ir1730-001/1.jpg"
      }
    ]
```


生成column_10的值为：

``` json
[
        {
            "costPrice": Int32("14"),
            "group_prices": [
                {
                    "group_id": "66b4926df455dd91ca3de33e",
                    "group_name": "svip",
                    "price": 16.00
                },
                {
                    "group_id": "66b4924ff455dd91ca3de33d",
                    "group_name": "vip",
                    "price": 18.00
                }
            ],
            "image": "/products/gx-ir1730-001/1.jpg",
            "marketPrice": 20.0,
            "name": "Original / Green · Approx. 5,000 pages.",
            "productId": "是sku的md5值",
            "sku": "GX-IR1730-001",
            "stock": Int32("1000000"),
            "weight": Int32("0")
        } 
    ]
```

注意，column_10的值是一个对象，你根据示例中的值对应【产品信息.json】中specs 的字段。你也可以映射好specs的字段后，让我确认一下再执行。

其他字段的值可以参照NewsContent表中这条数据的（_id为：ObjectId("6852a5100a8b42f2df141512")）