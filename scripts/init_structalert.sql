-- 配置表：存放需对比的对象名册
DROP TABLE IF EXISTS serviceordercenter.cfg_compare_objects;
CREATE TABLE serviceordercenter.cfg_compare_objects (
  id int(11) NOT NULL AUTO_INCREMENT,
  object_name varchar(200) NOT NULL COMMENT '对象名称，如表名、视图名',
  object_type varchar(20) NOT NULL DEFAULT 'TABLE' COMMENT '对象类型：TABLE, VIEW, PROCEDURE, FUNCTION',
  is_active tinyint(4) NOT NULL DEFAULT '1' COMMENT '是否开启对比: 1是，0否',
  need_sync tinyint(4) NOT NULL DEFAULT '0' COMMENT '是否需要同步数据: 1是，0否',
  date_column varchar(200) DEFAULT NULL COMMENT '迁移参考字段',
  create_time datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  update_time datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY idx_name_type (object_name,object_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='预警系统：配置比对对象表';

-- 日志表：按批次记录差异详情与目标修复 DDL
DROP TABLE IF EXISTS serviceordercenter.cfg_compare_diff;
CREATE TABLE serviceordercenter.cfg_compare_diff (
  id int(11) NOT NULL AUTO_INCREMENT,
  compare_date date NOT NULL COMMENT '比对所属日期（批次号）',
  object_name varchar(200) NOT NULL COMMENT '存在差异的对象名',
  object_type varchar(20) NOT NULL COMMENT '对象类型：TABLE, VIEW, PROCEDURE, FUNCTION',
  diff_detail json DEFAULT NULL COMMENT 'JSON格式：差异详情描述',
  target_ddl text COMMENT '待向目标库执行的手动同步 DDL',
  status varchar(20) NOT NULL DEFAULT 'PENDING' COMMENT '处理状态：PENDING（未处理）, RESOLVED（已解决）, IGNORED（忽略）',
  create_time datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  update_time datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_compare_date (compare_date),
  KEY idx_object_status (object_name,status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='预警系统：对象结构差异对比日志表';

INSERT INTO serviceordercenter.cfg_compare_objects (object_name, object_type, is_active, need_sync, create_time, update_time) 
SELECT a.TABLE_NAME,'TABLE',1,0,NOW(),NOW()
FROM information_schema.TABLES a,
information_schema.TABLES b
WHERE a.TABLE_SCHEMA='serviceordercenter'
  AND b.TABLE_SCHEMA='serviceordercenterhis'
  AND a.TABLE_NAME=b.TABLE_NAME
  AND a.TABLE_TYPE='BASE TABLE'
  AND b.TABLE_TYPE='BASE TABLE'
UNION
SELECT a.TABLE_NAME,'VIEW',1,0,NOW(),NOW()
FROM information_schema.TABLES a,
information_schema.TABLES b
WHERE a.TABLE_SCHEMA='serviceordercenter'
  AND b.TABLE_SCHEMA='serviceordercenterhis'
  AND a.TABLE_NAME=b.TABLE_NAME
  AND a.TABLE_TYPE='VIEW'
  AND b.TABLE_TYPE='VIEW'
UNION
SELECT a.ROUTINE_NAME,'PROCEDURE',1,0,NOW(),NOW()
FROM information_schema.ROUTINES a,
information_schema.ROUTINES b
WHERE a.ROUTINE_SCHEMA='serviceordercenter'
  AND b.ROUTINE_SCHEMA='serviceordercenterhis'
  AND a.ROUTINE_NAME=b.ROUTINE_NAME
  AND a.ROUTINE_TYPE='PROCEDURE'
  AND b.ROUTINE_TYPE='PROCEDURE'
UNION
SELECT a.ROUTINE_NAME,'FUNCTION',1,0,NOW(),NOW()
FROM information_schema.ROUTINES a,
information_schema.ROUTINES b
WHERE a.ROUTINE_SCHEMA='serviceordercenter'
  AND b.ROUTINE_SCHEMA='serviceordercenterhis'
  AND a.ROUTINE_NAME=b.ROUTINE_NAME
  AND a.ROUTINE_TYPE='FUNCTION'
  AND b.ROUTINE_TYPE='FUNCTION';

UPDATE cfg_compare_objects
SET need_sync=1
WHERE object_name IN
('api_application',
'api_applicationkey',
'basic_afcprocostinfo',
'basic_productcoopbrand',
'basic_sproleinfo',
'tb_goodsreplacehis',
'basic_workflowstatus',
'basic_apollo',
'basic_datadictionary',
'customer_basezone',
'tb_settlecondetail',
'tb_settleconfiginfo',
'tb_subjectlog_mall',
'tb_riskhistoryorder',
'tb_require_label',
'tb_require_earlywarning',
'tb_riskrequire',
'tb_behavior',
'tb_servicesubject',
'tb_servicesubjectdetail',
'tb_pricingmethod',
'basic_workstepinfo',
'workflowitems',
'basic_workflownoderelation',
'basic_operation',
'basic_ruleiteminfo',
'basic_serviceprovider',
'basic_spworkflowitem',
'basic_ruleinfo',
'basic_rulegroupinfo',
'tb_subjectclass',
'trans_customertag',
'tb_custarea',
'basic_installlocation',
'basic_productcooperation',
'basic_productcoopdetail',
'basic_installmaterialtype',
'basic_ordertypeinfo',
'basic_repetitivevin',
'basic_schedpolicy',
'basic_schedpolicyitem',
'tb_userarea',
'tb_datadefinition',
'tb_datadefinition_detail',
'common_rulematchconditions',
'tb_staffacquisitiontaginfo',
'tb_staffacquisitioninfo',
'common_entityinfo',
'common_entitysuit',
'common_propertyinfo',
'common_propertyother',
'common_listshowproperty',
'common_subruleinfo',
'tb_require_match_other',
'basic_teaminfo',
'tb_require_matchconditions',
'basic_institutionalinfo',
'tb_require_warningreminder',
'tb_indicator',
'tb_indicatorformula_data',
'tb_indicatorrange',
'tb_indicatorformula',
'basic_departinfo',
'basic_orgroleinfo',
'common_propertymapping',
'tb_workorderdetailmodel',
'tb_useraddress',
'common_rulematchrelation',
'tb_goodsreplace',
'common_listsearchproperty',
'tb_userinfo_serv',
'basic_district',
'basic_ordercooperation',
'tb_userclockininfo',
'au_ehcfrule003',
'ehr_userinfo',
'au_afcrule001',
'common_rulematchnodes',
'basic_schedpolicydetail',
'basic_ordercoopdetail',
'tb_userrulegroupinfo',
'tb_userruleinfo',
'basic_userpermission',
'df_labelinfo_history',
'rp_areacomplete',
'rp_workcomplete',
'membership_wechat',
'au_ehcfrule002',
'common_ruleactionlog',
'tb_userruleiteminfo',
'tb_userdetail',
'tb_feeiteminfo',
'workflownodeactions',
'workflownodeactors',
'workflownoderelatedactors',
'workflownodestepconditions',
'workflownodes',
'basic_userruleinfo',
'basic_accessoryresource',
'basic_custconfirmrule',
'basic_accessoryrule',
'tb_userinfo',
'basic_custspecialconfig',
'basic_accessoryinfo',
'basic_schedpolicymultiperson',
'au_ehcfrule001');
