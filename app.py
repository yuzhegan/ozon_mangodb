# encoding='utf-8

# @Time: 2024-04-09
# @File: %
#!/usr/bin/env

from icecream import ic
import os
from pydantic import BaseModel
from pymongo import MongoClient
from typing import Union
from fastapi.middleware.cors import CORSMiddleware
import json
import uvicorn
from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder  # 导入jsonable_encoder来处理MongoDB文档
from bson import ObjectId


app = FastAPI()

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = MongoClient("mongodb://127.0.0.1:27017/")
db = client["ozon"]
collection_category = db['ozon_category']  # 类目数据
collection_product = db['ozon_product']  # 详情数据
collection_save_product = db['save_product']  # 保存数据

def convert_query(query):
    converted_query = {}
    for key, value in query.items():
        if isinstance(value, dict) and 'min' in value or 'max' in value:
            converted_value = {}
            if 'max' in value:
                converted_value['$lt'] = float(value['max'])
                converted_query[key] = converted_value
            if 'min' in value:
                converted_value['$gte'] = float(value['min'])
                converted_query[key] = converted_value
        else:
            converted_query[key] = value
    return converted_query


class Product(BaseModel):  # 定义一个保存模型
    ID: str



@app.post("/save_product/")
async def save_product(product: Product):
    product_dict = product.dict()
    collection_save_product.insert_one(product_dict)
    return f"产品 {product_dict['ID']} 保存成功"
@app.post("/del_product/")
async def del_product(product: Product):
    product_dict = product.dict()
    collection_save_product.delete_one(product_dict)
    return f"产品 {product_dict['ID']} 删除成功"


@app.get("/get_save_product/")
async def SearchProduct(page: int = 1):
    skip = (page - 1) * 50
    cursor = collection_save_product.distinct("ID")
    id_list = [int(id) for id in cursor]
    ic(id_list)
    result = collection_product.find({"ID": {"$in": id_list}}, {"_id":0}).limit(50).skip(skip)

    return list(result)



class Category(BaseModel):
    label: list
    formdata: dict
    page: int = 1  # 这里应该是类属性，不是字典的一部分
    sort: dict = {"28日销量":"ascending"}

@app.get("/")
async def read_root():
    return {"Hello": "World"}

@app.get("/items/{item_id}")
async def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}

@app.post("/category/")
async def create_category_list(category: Category):
    category_dict = category.dict()  # 将模型转换为字典
    page = category.page
    per_page = 50
    skip = (page - 1) * per_page
    limit = per_page
    formdata = category_dict['formdata']
    ic(formdata)
    # 转化为MongoDB查询语句
    serializable_result = []
    if len(category.label) == 0:
        return "No label"
    elif len(category.label) == 1:
        if "All" in category.label:
            query = {}
        else:
            # 一级类目
            category1 = category.label[0]
            query = {
                "一级分类": category1,  # 假设这里使用传入的类别
            }
    elif len(category.label) == 2:
        category1 = category.label[0]
        if "All" in category.label:
            query = {"一级分类": category1}
        else:
            category2 = category.label[1]
            query = {
                "一级分类": category1,
                "二级分类": category2
                    }
    elif len(category.label) == 3:
        category1 = category.label[0]
        category2 = category.label[1]
        if "All" in category.label:
            query = {"一级分类": category1,
                     "二级分类": category2}
        else:
            category3 = category.label[2]
            query = {
                "一级分类": category1,
                "二级分类": category2,
                "三级分类": category3
            }
    query.update(formdata)
    query = {key: value for key, value in query.items() if value != {}}
    query = convert_query(query)
    try:
        if query['ID']:
            query['ID'] = int(query['ID'])
    except Exception as e:
        ic(e)
    sorts_dict = category_dict.sort
    if not sorts_dict:
        sorts_dict.sort = {"28日销量":"descending"}
    for key, value in sorts_dict.items():
        if value == "descending":
            sorts_dict[key] = -1
        else:
            sorts_dict[key] = 1
    result = collection_category.find(query, {"_id":0}).sort(sorts_dict).skip(skip).limit(limit)
    # result = collection_category.find(query, {"_id":0}).skip(skip).limit(limit)
    
    # 将MongoDB文档转换为可序列化的格式
    # for doc in result:
    #     doc['_id'] = str(doc['_id'])  # 将ObjectId转换为字符串
    #     serializable_result.append(doc)
    return list(result)


@app.post("/Product/")
async def create_product_list(product: Category):
    product_dict = product.dict()  # 将模型转换为字典
    page = product.page
    per_page = 50
    skip = (page - 1) * per_page
    limit = per_page
    formdata = product_dict['formdata']
    serializable_result = []
    
    
    if len(product.label) == 0:
        return "No label"
    elif len(product.label) == 1:
        if "All" in product.label:
            query = {}
        # 一级类目
        else:
            category1 = product.label[0]
            query = {
                "一级分类": category1,  # 假设这里使用传入的类别
            }
    elif len(product.label) == 2:
        category1 = product.label[0]
        if "All" in product.label:
            query = {"一级分类": category1}
        else:
            category2 = product.label[1]
            query = {
                "一级分类": category1,
                "二级分类": category2
            }
    elif len(product.label) == 3:
        category1 = product.label[0]
        category2 = product.label[1]
        if "All" in product.label:
            query = {"一级分类": category1,
                     "二级分类": category2}
        else:
            category3 = product.label[2]
            query = {
                "一级分类": category1,
                "二级分类": category2,
                "三级分类": category3
            }
    elif len(product.label) == 4:
        category1 = product.label[0]
        category2 = product.label[1]
        category3 = product.label[2]
        if "All" in product.label:
            query = {"一级分类": category1,
                     "二级分类": category2,
                     "三级分类": category3}
        else:
            category4 = product.label[3]
            query = {
                "一级分类": category1,
                "二级分类": category2,
                "三级分类": category3,
                "四级分类": category4
            }
    query.update(formdata)
    ic(formdata)
    query = {key: value for key, value in query.items() if value != {}}
    query = convert_query(query)
    ic(query)
    try:
        if query['ID']:
            query['ID'] = int(query['ID'])
    except Exception as e:
        ic(e)
    ic(query)
    if not product_dict.sort:
        product_dict.sort = {"28日销量":"descending"}

    sorts_dict = product_dict.sort
    for key, value in sorts_dict.items():
        if value == "descending":
            sorts_dict[key] = -1
        else:
            sorts_dict[key] = 1
    result = collection_category.find(query, {"_id":0}).sort(sorts_dict).skip(skip).limit(limit)
    #不返回_id
    # result = collection_product.find(query, {"_id":0}).skip(skip).limit(limit)
    
    # 将MongoDB文档转换为可序列化的格式
    # for doc in result:
    #     doc['_id'] = str(doc['_id'])  # 将ObjectId转换为字符串
    #     serializable_result.append(doc)
    return list(result)






if __name__ == "__main__":
    uvicorn.run("app:app", reload=True, port=5050, host="0.0.0.0")
