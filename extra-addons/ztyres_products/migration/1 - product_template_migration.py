import psycopg2 as pg
import pandas.io.sql as psql
import os



connection = pg.connect("host=192.168.1.239 port=5432 dbname=Z16 user=odoo password=a750105530A12345")
base_module = 'ztyres_products_'
break_line = os.linesep
#New name,Old name
colums_to_migrate = [
('tire_measure','x_studio_medida_1'),
('face','x_studio_cara'),
('layer','x_studio_capas'),
('manufacturer','x_studio_fabricante'),
('brand','x_studio_marca'),
('model','x_studio_modelo_1'),
('speed','x_studio_ndice_de_velocidad'),
('index_of_load','x_studio_indice_carga'),
('wholesale_rebate','x_studio_rm'),
#('country_id','x_studio_origen'),
('segment','x_studio_uso'),
('tier','x_studio_posicionamiento'),
('type','x_studio_segmento'),
('supplier_segment','x_studio_segmento_proveedor'),
('original_equipment','x_studio_eo'),
('e_mark','x_studio_e_mark'),
('s_mark','x_studio_s_mark'),
('ccc','x_studio_ccc')
##Falta res country que es origen
]

with open('/mnt/extra-addons/ztyres_products/migration/inserts.sql', 'w') as f:
    for column in colums_to_migrate:    
        query2 = 'select distinct %s from product_template;'%(column[1])
        df_unique_values = psql.read_sql(query2, connection).sort_values(by=[column[1]])
        insert = 'INSERT INTO public.%s%s (name) VALUES '%(base_module,column[0])
        values_to_insert = ''
        for index, row in df_unique_values.iterrows():        
            values_to_insert += """("%s"),"""%(str(row[column[1]]))
        insert =insert+values_to_insert[:-1]+';'
        insert=insert.replace('"',"'")
        print(insert)    
        f.write(insert + break_line)
    f.close()