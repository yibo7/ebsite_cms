# 自动接库API
提供此接口是为了方便AI自动内容创作时提交内容使用，调用端点：
> /api/auto_post_content/<int:user_id>/<int:class_id>/<md5:site_key_md5>

- user_id：用户的整数ID
- class_id：分类ID
- site_key_md5：网站密钥的MD5值

调用示例：

    POST: /api/auto_post_content/21/7/4224d63787d56b5a200bbfbc8eb8f3d9
    可用参数：add_time, title, info, small_pic, class_name, class_id, class_n_id, seo_title, seo_keyword, seo_description, hits, comment_num, favorable_num, user_id, user_name, user_ni_name, rand_num, is_good,  id, column_1, column_2, column_3, column_4, column_5, column_6, column_7, column_8, column_9, column_10, column_11, column_12, column_13, column_14, column_15, column_16, column_17, column_18, column_19, column_20, column_21
    有一个特殊的字段tag不能直接传递，需要通过tagstr参数传递，多个标签可用英文逗号分开