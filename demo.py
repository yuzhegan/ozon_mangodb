# encoding='utf-8

# @Time: 2024-04-08
# @File: %
#!/usr/bin/env
from icecream import ic
import os
import polars as pl
import pandas as pd
import math
import time



class ozonMangodb():
    def __init__(self, file_path, settings_path):
        self.file_path = file_path
        self.settings_path = settings_path
        # self.df = pd.read_excel(self.file_path)
        # self.df = self.df.fillna("None", inplace=True)
        # self.df = pl.from_pandas(self.df)
        # self.df = pl.read_excel(self.file_path)
        self.df = pl.read_excel(file_path,
                                schema_overrides={"可用性 (%)": pl.Float64, '因缺货而错过的订单金额（₽）':pl.Float64,},

        )
        print("有{}行数据".format(len(self.df)))
        self.columns_name = self.df.columns
        self.settings = pl.read_excel(self.settings_path)
        self.str_today = time.strftime('%Y-%m-%d', time.localtime(time.time()))

    def loaddatas(self):
        #1.1 get cetegory columns
        new_columns_name = self.settings['列名中文'].drop_nulls().to_list()
        # change df columns name
        df = self.df.rename({self.columns_name[i]: new_columns_name[i] for i in range(len(self.columns_name))})

        catagory2_dict = self.settings.select(['二级类别','二级分类']).drop_nulls()
        catagory3_dict = self.settings.select(['三级类别','三级分类']).drop_nulls()
        catagory4_dict = self.settings.select(['四级类别','四级分类']).drop_nulls()

        df = df.join(catagory2_dict,how='left',on='二级类别',left_on='二级类别',right_on='二级类别',suffix='_x')
        df = df.join(catagory3_dict,how='left',on='三级类别',left_on='三级类别',right_on='三级类别',suffix='_x')
        df = df.join(catagory4_dict,how='left',on='四级类别',left_on='四级类别',right_on='四级类别',suffix='_x')
        # 添加一级分类
        df = df.with_columns([(pl.lit('住宅与花园').alias('一级分类'))])


        # df.write_excel('./ozon_mangodb/ozon_test_output.xlsx')
        ic(df.schema)
        df = df.with_columns([(pl.col('28日销售额')/pl.col('28日订单均价')).alias('28日销量'),
                              (pl.lit(10)).alias('越库费'),
                              ((pl.col('28日订单均价')*0.17).map_elements(lambda x: math.ceil(x), return_dtype=pl.Float64)
                               ).alias('类目佣金'),  # 向上取整
                              ((pl.col('28日订单均价')*0.01).map_elements(lambda x: math.ceil(x), return_dtype=pl.Float64)
                               ).alias('平台收单费'),  # 向上取整
                              (pl.lit(32).alias('物流')),
                              ((pl.col('28日订单均价')*0.055).map_elements(lambda x: math.ceil(x), return_dtype=pl.Float64)
                               ).alias('最后一公里'),

                              ])
        df = df.with_columns([
            (pl.col('28日订单均价') - pl.col('越库费') - pl.col('类目佣金') - pl.col('平台收单费') - pl.col('物流') - pl.col('最后一公里')).alias('毛利润')
        ])



        # 第二步：使用已经存在的"毛利润"列计算"毛利润率"
        df = df.with_columns([
            (pl.col('毛利润') / pl.col('28日订单均价')).alias('毛利润率')
        ])

        # 获取ozon_ID 作为唯一标识
        df = df.with_columns([
            (pl.col('商品链接').map_elements(lambda x: x.split('/')[-1], return_dtype=pl.Utf8)).alias('ID')
        ])
        df = df.with_columns(
                pl.lit(self.str_today).alias("Updatetime")
                )

        return df

    def GenPivotDatas(self, df):
        # exit()
        # 透视表
        plvt = df.group_by(['一级分类','二级分类', '三级分类', '四级分类']).agg([pl.col('商品链接').count().alias('类目产品数量'),
                                                         pl.col('28日销量').sum().alias(
            '28日销量'),
            pl.col('28日销售额').sum().alias(
            '28日销售额'),
            pl.col('28日订单均价').mean().alias(
            '28日订单均价'),
            pl.col('发货仓库数量（个）').max().alias(
            '仓库数量'),
            pl.col('交货时间（天）').mean().alias(
            '交货天数'),
            pl.col('广告费用占比 (%)').mean().alias(
            '广告费'),
            pl.col('因缺货而错过的订单金额（₽）').sum().alias(
            '缺货错失销售额')
        ]).sort(by='28日销售额', descending=True)
        plvt = plvt.with_columns(
            pl.lit(self.str_today).alias("Updatetime")
                )
        return plvt


if __name__ == '__main__':
    file_path = './ozon住宅与花园1.2.xlsx'
    # file_path = './data.xlsx'
    settings_path = './设置.xlsx'
    ozondb = ozonMangodb(file_path, settings_path)
    df = ozondb.loaddatas()
    df.write_csv('./ozon_test_output.csv')
    plvt = ozondb.GenPivotDatas(df)
    plvt.write_csv('./ozon_test_output_pivot.csv')

