select * 
from cfg_compare_objects a
where need_sync=1
  and date_column is null;

update cfg_compare_objects a
set a.date_column='CreatedAt'
where need_sync=1
  and date_column is null
  and exists(select 1
  from information_schema.COLUMNS b
  WHERE b.TABLE_NAME=a.object_name
  AND b.TABLE_SCHEMA='serviceordercenter'
  AND b.COLUMN_NAME='CreatedAt'
);

update cfg_compare_objects a
set a.date_column='InserTime'
where need_sync=1
  and date_column is null
  and exists(select 1
  from information_schema.COLUMNS b
  WHERE b.TABLE_NAME=a.object_name
  AND b.TABLE_SCHEMA='serviceordercenter'
  AND b.COLUMN_NAME='InserTime'
);

update cfg_compare_objects a
set a.date_column='InsertTime'
where need_sync=1
  and date_column is null
  and exists(select 1
  from information_schema.COLUMNS b
  WHERE b.TABLE_NAME=a.object_name
  AND b.TABLE_SCHEMA='serviceordercenter'
  AND b.COLUMN_NAME='InsertTime'
);

update cfg_compare_objects a
set a.date_column='LastUpdateTimeStamp'
where need_sync=1
  and date_column is null
  and exists(select 1
  from information_schema.COLUMNS b
  WHERE b.TABLE_NAME=a.object_name
  AND b.TABLE_SCHEMA='serviceordercenter'
  AND b.COLUMN_NAME='LastUpdateTimeStamp'
);

ALTER TABLE `serviceordercenter`.`tb_riskhistoryorder` 
ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '数据变更时间戳' AFTER `Deleted`;

ALTER TABLE `serviceordercenter`.`tb_servicesubjectdetail` 
ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '数据变更时间戳';

ALTER TABLE `serviceordercenter`.`tb_userdetail` 
ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '数据变更时间戳';

############全用最后更新时间

update cfg_compare_objects a
  set date_column=null
where need_sync=1
  and date_column is not null;

update cfg_compare_objects a
set a.date_column='LastUpdateTimeStamp'
where need_sync=1
  and date_column is null
  and exists(select 1
  from information_schema.COLUMNS b
  WHERE b.TABLE_NAME=a.object_name
  AND b.TABLE_SCHEMA='serviceordercenter'
  AND b.COLUMN_NAME='LastUpdateTimeStamp'
);

select CONCAT('ALTER TABLE `serviceordercenter`.',object_name,' ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT ''数据变更时间戳'';')
from cfg_compare_objects a
where need_sync=1
  and date_column is null;

update cfg_compare_objects a
set a.date_column='LastUpdateTimeStamp'
where need_sync=1
  and date_column is null
  and exists(select 1
  from information_schema.COLUMNS b
  WHERE b.TABLE_NAME=a.object_name
  AND b.TABLE_SCHEMA='serviceordercenter'
  AND b.COLUMN_NAME='LastUpdateTimeStamp'
);