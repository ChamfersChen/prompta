import mysql_ds from '@/assets/datasource/icon_mysql.png'
import excel from '@/assets/datasource/icon_excel.png'
import oracle from '@/assets/datasource/icon_oracle.png'
import pg from '@/assets/datasource/icon_PostgreSQL.png'
import sqlServer from '@/assets/datasource/icon_SQL_Server.png'
import ck from '@/assets/datasource/icon_ck.png'
import dm from '@/assets/datasource/icon_dm.png'
import doris from '@/assets/datasource/icon_doris.png'
import redshift from '@/assets/datasource/icon_redshift.png'
import es from '@/assets/datasource/icon_es.png'
import kingbase from '@/assets/datasource/icon_kingbase.png'
import starrocks from '@/assets/datasource/icon_starrocks.png'

export const dsType = [
  { label: 'MySQL', value: 'mysql' },
  { label: 'Oracle', value: 'oracle' },
  { label: 'PostgreSQL', value: 'pg' },
  { label: 'SQL Server', value: 'sqlServer' },
  { label: 'ClickHouse', value: 'ck' },
  { label: '达梦', value: 'dm' },
  { label: 'Apache Doris', value: 'doris' },
  { label: 'AWS Redshift', value: 'redshift' },
  { label: 'Elasticsearch', value: 'es' },
  { label: 'Kingbase', value: 'kingbase' },
  { label: 'StarRocks', value: 'starrocks' },
]

export const dsTypeWithImg = [
  // { name: 'local_excelcsv', type: 'excel', img: excel, description: '' },
  { name: 'MySQL', type: 'mysql', img: mysql_ds, description: '1' },
  { name: 'PostgreSQL', type: 'pg', img: pg, description: '2' },
  { name: 'Oracle', type: 'oracle', img: oracle, description: '' },
  { name: 'SQL Server', type: 'sqlServer', img: sqlServer, description: '' },
  { name: 'ClickHouse', type: 'ck', img: ck, description: '' },
  { name: '达梦', type: 'dm', img: dm, description: '' },
  { name: 'Apache Doris', type: 'doris', img: doris, description: '' },
  { name: 'AWS Redshift', type: 'redshift', img: redshift, description: '' },
  { name: 'Elasticsearch', type: 'es', img: es, description: '' },
  { name: 'Kingbase', type: 'kingbase', img: kingbase, description: '' },
  // { name: 'StarRocks', type: 'starrocks', img: starrocks, description: '' },
]

export const haveSchema = ['sqlServer', 'pg', 'oracle', 'dm', 'redshift', 'kingbase']
