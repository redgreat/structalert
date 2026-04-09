ALTER TABLE `api_application` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `api_applicationkey` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `basic_accessoryinfo` ADD COLUMN `IsBundingAsset` smallint(6) NULL   COMMENT '是否绑定租赁物：（0.否；1.是；）';
ALTER TABLE `basic_accessoryinfo` ADD COLUMN `IsUnusual` smallint(6) NULL   COMMENT '是否存在异常：(0.否；1.是；2.适用全部；)';
ALTER TABLE `basic_accessoryinfo` ADD COLUMN `IsPostUpload` smallint(6) NULL   COMMENT '是否邮寄上传(0否1是)';
ALTER TABLE `basic_accessoryinfo` ADD COLUMN `IsDisplayExample` smallint(6) NULL   COMMENT '是否展示示例图(0否1是)';
ALTER TABLE `basic_accessoryinfo` ADD COLUMN `DeviceUniqueNo` smallint(6) NULL   COMMENT '设备唯一标识：（0.不存在；1.存在；2.适用全部；）';
ALTER TABLE `basic_accessoryinfo` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `basic_accessoryresource` ADD COLUMN `ResourceClassName` varchar(50) NULL   COMMENT '附件类别';
ALTER TABLE `basic_accessoryresource` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `basic_accessoryrule` MODIFY COLUMN `RemindContent` varchar(500) NULL   COMMENT '提醒内容';
ALTER TABLE `basic_accessoryrule` ADD COLUMN `RuleModule` smallint(6) NULL DEFAULT '0'  COMMENT '规则模块（区分配置的第几个模块的客户要求）';
ALTER TABLE `basic_accessoryrule` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `basic_afcprocostinfo` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `basic_apollo` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `basic_custconfirmrule` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `basic_custspecialconfig` ADD COLUMN `ServiceProviderCode` varchar(50) NULL   COMMENT '服务商Code(basic_serviceprovider.ProviderCode)';
ALTER TABLE `basic_custspecialconfig` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `basic_datadictionary` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `basic_district` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `basic_installlocation` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `basic_installmaterialtype` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `basic_operation` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `basic_ordercoopdetail` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `basic_ordercooperation` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `basic_ordertypeinfo` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `basic_orgroleinfo` ADD COLUMN `ApiPermission` json NULL   COMMENT 'Api角色权限验证';
ALTER TABLE `basic_orgroleinfo` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `basic_productcoopbrand` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `basic_productcoopdetail` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `basic_productcooperation` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `basic_repetitivevin` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `basic_resourceitem` ADD COLUMN `FileSource` smallint(6) NULL   COMMENT '附件上传来源：1.现场拍照；2.相册上传；3.PC上传；';
ALTER TABLE `basic_schedpolicy` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `basic_schedpolicydetail` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `basic_schedpolicyitem` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `basic_schedpolicymultiperson` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `basic_serviceprovider` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `basic_sproleinfo` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `basic_spworkflowitem` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `basic_userpermission` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `basic_workflownoderelation` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `basic_workflowstatus` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `basic_workstepinfo` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `common_entityinfo` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `common_entitysuit` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `common_listsearchproperty` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `common_listshowproperty` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `common_propertyinfo` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `common_propertymapping` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `common_propertyother` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `common_rulematchconditions` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `common_rulematchnodes` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `common_rulematchrelation` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `common_subruleinfo` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `customer_basezone` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `df_labelinfo_history` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `ehr_userinfo` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `membership_wechat` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `move_workflowuserinfo` MODIFY COLUMN `BatchNo` double NULL   ;
ALTER TABLE `rp_afcworkorderdetail` ADD COLUMN `OverdueGrade` varchar(50) NULL   COMMENT '逾期账龄';
ALTER TABLE `rp_afcworkorderdetail` MODIFY COLUMN `AdjustReimbursableDistance` decimal(18,2) NULL   COMMENT '调整报销去程公里数';
ALTER TABLE `rp_afcworkorderdetail` ADD COLUMN `AdjustReimReturnDistance` decimal(18,2) NULL   COMMENT '调整报销返程公里数';
ALTER TABLE `rp_afcworkorderdetail` MODIFY COLUMN `CloseReasonName` varchar(200) NULL   COMMENT '关闭原因';
ALTER TABLE `rp_afcworkorderdetail` ADD COLUMN `FeeRemark` varchar(200) NULL   COMMENT '计价费用备注';
ALTER TABLE `rp_afcworkorderdetail` ADD COLUMN `FindWho` varchar(200) NULL   COMMENT '见到何人';
ALTER TABLE `rp_afcworkorderdetail` ADD COLUMN `ReturnCountReward` decimal(18,2) NULL   COMMENT '回款户数奖励';
ALTER TABLE `rp_afcworkorderdetail` ADD COLUMN `SecondLinkMan` varchar(500) NULL   COMMENT '复联人';
ALTER TABLE `rp_afcworkorderdetail` ADD COLUMN `SecondVisitStatus` varchar(20) NULL   COMMENT '(AFC)二访状态';
ALTER TABLE `rp_afcworkorderdetail` ADD COLUMN `ReturnPriceReward` decimal(18,2) NULL   COMMENT '回款额奖励';
ALTER TABLE `rp_afcworkorderdetail` ADD COLUMN `GovernmentDistance` decimal(18,2) NULL   COMMENT '派单地到政府距离字段';
ALTER TABLE `rp_afcworkorderdetail` ADD COLUMN `VisitorPlateNumber` varchar(20) NULL   COMMENT '上访车牌号';
ALTER TABLE `rp_afcworkorderdetail` ADD COLUMN `VisitorPowerType` varchar(20) NULL   COMMENT '上访动力输出';
ALTER TABLE `rp_afcworkorderdetail` ADD COLUMN `VisitorCarBrandName` varchar(50) NULL   COMMENT '上访车型';
ALTER TABLE `rp_afcworkorderdetail` ADD COLUMN `VisitorReferencePowerType` varchar(20) NULL   COMMENT '上访动力输出参考';
ALTER TABLE `rp_afcworkorderdetail` ADD COLUMN `WorkPhoneType` varchar(50) NULL   COMMENT '工作手机类型参考';
ALTER TABLE `rp_afcworkorderdetail` ADD COLUMN `AudioSpotCheck` varchar(50) NULL   COMMENT '录音抽检比例';
ALTER TABLE `rp_afcworkorderdetail` ADD COLUMN `ExamSubjectName` varchar(50) NULL   COMMENT '考核科目名称';
ALTER TABLE `rp_afcworkorderdetail` ADD COLUMN `ExamSubjectApplyReason` varchar(200) NULL   COMMENT '考核科目申请原因';
ALTER TABLE `rp_areacomplete` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `rp_vhsworkorderdetail` ADD COLUMN `FirstReturnAuditState` smallint(6) NULL   COMMENT '首次归还审核结果';
ALTER TABLE `rp_vhsworkorderdetail` ADD COLUMN `FirstReturnRejectReason` varchar(500) NULL   COMMENT '首次归还不合格原因';
ALTER TABLE `rp_vhsworkorderdetail` ADD COLUMN `ReceiveState` smallint(6) NULL   COMMENT '归还状态';
ALTER TABLE `rp_vhsworkorderdetail` ADD COLUMN `CollectState` smallint(6) NULL   COMMENT '收件状态';
ALTER TABLE `rp_vhsworkorderdetail` ADD COLUMN `FirstCollectAuditState` smallint(6) NULL   COMMENT '首次收件审核结果';
ALTER TABLE `rp_vhsworkorderdetail` ADD COLUMN `FirstCollectRejectReason` varchar(500) NULL   COMMENT '首次收件不合格原因';
ALTER TABLE `rp_vhsworkorderdetail` ADD COLUMN `PerformancePerCode` varchar(50) NULL   COMMENT '绩效人账号';
ALTER TABLE `rp_vhsworkorderdetail` ADD COLUMN `PerformancePerName` varchar(50) NULL   COMMENT '绩效人名称';
ALTER TABLE `rp_vhsworkorderdetail` ADD COLUMN `ActualRecordPersonCode` varchar(50) NULL   COMMENT '实际备案提交人账号';
ALTER TABLE `rp_vhsworkorderdetail` ADD COLUMN `ActualRecordPersonName` varchar(50) NULL   COMMENT '实际备案提交人名称';
ALTER TABLE `rp_vhsworkorderinfodetail` MODIFY COLUMN `AppointLinkResult` varchar(600) NULL   COMMENT '改约联系结果';
ALTER TABLE `rp_vhsworkorderinfodetail` ADD COLUMN `ReceiveState` smallint(6) NULL   COMMENT '归还状态';
ALTER TABLE `rp_vhsworkorderinfodetail` ADD COLUMN `FirstReturnAuditState` smallint(6) NULL   COMMENT '首次归还审核结果';
ALTER TABLE `rp_vhsworkorderinfodetail` ADD COLUMN `FirstReturnRejectReason` varchar(500) NULL   COMMENT '首次归还不合格原因';
ALTER TABLE `rp_vhsworkorderinfodetail` ADD COLUMN `CollectState` smallint(6) NULL   COMMENT '收件状态';
ALTER TABLE `rp_vhsworkorderinfodetail` ADD COLUMN `FirstCollectAuditState` smallint(6) NULL   COMMENT '首次收件审核结果';
ALTER TABLE `rp_vhsworkorderinfodetail` ADD COLUMN `FirstCollectRejectReason` varchar(500) NULL   COMMENT '首次收件不合格原因';
ALTER TABLE `rp_vhsworkorderinfodetail` ADD COLUMN `PerformancePerCode` varchar(50) NULL   COMMENT '绩效人账号';
ALTER TABLE `rp_vhsworkorderinfodetail` ADD COLUMN `PerformancePerName` varchar(50) NULL   COMMENT '绩效人名称';
ALTER TABLE `rp_workcomplete` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `rp_workordercount` ADD COLUMN `ServiceDepartId` char(36) NULL   COMMENT '施工人部门Id';
ALTER TABLE `rp_workordercount` ADD COLUMN `ServiceDepartName` varchar(100) NULL   COMMENT '施工人部门名称';
ALTER TABLE `tb_abnormalorder_log` ADD COLUMN `MessageRemindJson` json NULL   COMMENT '企业微信消息提醒JSON';
ALTER TABLE `tb_abnormalorder_log` ADD COLUMN `LastUpdatedTimestamp` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '最后一次更新时间';
ALTER TABLE `tb_afcnegotiationrecordinfo` ADD COLUMN `ConnectChannel` smallint(6) NULL   COMMENT '沟通渠道（0-其他，1-通话，2-短信，3-微信）';
ALTER TABLE `tb_afcnegotiationrecordinfo` ADD COLUMN `UserTel` varchar(20) NULL   COMMENT '手机号';
ALTER TABLE `tb_afcnegotiationrecordinfo` ADD COLUMN `UserName` varchar(50) NULL   COMMENT '姓名';
ALTER TABLE `tb_afcnegotiationrecordinfo` ADD COLUMN `WxRemark` varchar(50) NULL   COMMENT '微信备注';
ALTER TABLE `tb_afcnegotiationrecordinfo` ADD COLUMN `WxCode` varchar(50) NULL   COMMENT '微信号';
ALTER TABLE `tb_afcnegotiationrecordinfo` ADD COLUMN `VisitorTel` varchar(20) NULL   COMMENT '本人手机号';
ALTER TABLE `tb_afcpaymentreport` ADD COLUMN `ReturnedType` smallint(6) NULL   COMMENT '回款类型：1.正常提报；2.回款补录；';
ALTER TABLE `tb_afcpaymentreport` ADD COLUMN `LastApprovalTime` datetime NULL   COMMENT '最新审批时间（只更新审核通过和审核拒绝时间）';
ALTER TABLE `tb_afcpaymentreport` ADD COLUMN `LastApprovalName` varchar(50) NULL   COMMENT '最新审批回款人姓名';
ALTER TABLE `tb_afcpaymentreport` ADD COLUMN `LastApprovalCode` varchar(50) NULL   COMMENT '最新审批回款人账号';
ALTER TABLE `tb_afcpaymentreport` ADD COLUMN `InitialReturnedTypeCode` varchar(20) NULL   COMMENT '初始回款类型（basic_dictionary.code）';
ALTER TABLE `tb_afcpaymentreport` ADD COLUMN `ParentReturnedId` char(12) NULL   COMMENT '回款补录所属回款提报Id';
ALTER TABLE `tb_afcpaymentreport` ADD COLUMN `ParentReturnedCode` varchar(50) NULL   COMMENT '回款补录所属回款提报编号';
ALTER TABLE `tb_afcworkfinanceinfo` MODIFY COLUMN `PaymentPeriod` varchar(100) NULL   COMMENT '已还期数';
ALTER TABLE `tb_afcworkfinanceinfo` ADD COLUMN `EntrustAmount` decimal(18,2) NULL   COMMENT '委案金额';
ALTER TABLE `tb_afcworkfinanceinfo` ADD COLUMN `Performance` varchar(500) NULL   COMMENT '协催绩效';
ALTER TABLE `tb_afcworkorderinfo` ADD COLUMN `CustomerBriefName` varchar(100) NULL   COMMENT '客户简称';
ALTER TABLE `tb_afcworkorderinfo` ADD COLUMN `AdjustReimReturnDistance` decimal(18,2) NULL   COMMENT '调整报销返程公里数';
ALTER TABLE `tb_afcworkorderinfo` ADD COLUMN `ExamSubjectCode` varchar(50) NULL   COMMENT '考核科目编码';
ALTER TABLE `tb_afcworkorderinfo` ADD COLUMN `ExamSubjectName` varchar(50) NULL   COMMENT '考核科目名称';
ALTER TABLE `tb_afcworkorderinfo` ADD COLUMN `ProjectId` char(12) NULL   COMMENT '所属项目Id';
ALTER TABLE `tb_afcworkorderinfo` ADD COLUMN `ProjectName` varchar(50) NULL   COMMENT '所属项目';
ALTER TABLE `tb_appointauditinfo` ADD COLUMN `WorkOrderId` varchar(36) NULL   COMMENT '工单主单主键(tb_workorderinfo.Id)';
ALTER TABLE `tb_behavior` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `tb_chpworkorderinfo` ADD COLUMN `LastAuditRejectRemark` varchar(100) NULL   COMMENT '最后一次安装驳回原因';
ALTER TABLE `tb_chpworkorderinfo` ADD COLUMN `LastUpdateTimeStamp` timestamp(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) on update CURRENT_TIMESTAMP(3) COMMENT '最近更新时间';
ALTER TABLE `tb_custarea` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `tb_datadefinition` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `tb_datadefinition_detail` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `tb_exportlog` ADD COLUMN `ExpStatus` smallint(6) NULL   COMMENT '导出状态(0等待提交1导出中2导出完成3导出失败)';
ALTER TABLE `tb_feeiteminfo` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `tb_goodsreplace` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `tb_goodsreplacehis` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `tb_indicator` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `tb_indicatorformula` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `tb_indicatorformula_data` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `tb_indicatorrange` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `tb_require_earlywarning` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `tb_require_label` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `tb_require_match_other` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `tb_require_matchconditions` MODIFY COLUMN `LoanType` varchar(20) NULL   COMMENT '放款类型(0先抵后放 1先放后抵 2空)';
ALTER TABLE `tb_require_matchconditions` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `tb_require_warningreminder` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `tb_riskhistoryorder` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `tb_riskrequire` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `tb_servicesubject` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `tb_servicesubjectdetail` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `tb_settlecondetail` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `tb_settleconfiginfo` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `tb_staffacquisitioninfo` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `tb_staffacquisitiontaginfo` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `tb_subjectclass` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `tb_subjectlog_mall` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `tb_useraddress` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `tb_userarea` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `tb_userdetail` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `tb_userinfo` ADD COLUMN `SettleType` smallint(6) NULL DEFAULT '2'  COMMENT '人员结算类型：0.不结算；1.现结；2.月结；3.周结；';
ALTER TABLE `tb_userinfo` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `tb_userinfo_serv` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `tb_userrulegroupinfo` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `tb_userruleinfo` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `tb_userruleiteminfo` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `tb_vhsworkorderinfo` ADD COLUMN `RecordPersonCode` varchar(50) NULL   COMMENT '备案提交人账号';
-- 虚拟列 v_ToBeAuditTag 需要手动处理，类型: smallint(6), 存储: VIRTUAL
-- 虚拟列 v_tirePlateNumber 需要手动处理，类型: varchar(20), 存储: VIRTUAL
-- 虚拟列 v_tireDeviceModel 需要手动处理，类型: varchar(200), 存储: VIRTUAL
-- 虚拟列 v_tireNeedOuterTireRemoval 需要手动处理，类型: smallint(6), 存储: VIRTUAL
-- 虚拟列 v_tireRemovalCount 需要手动处理，类型: int(11), 存储: VIRTUAL
-- 虚拟列 v_tireInstallationMethod 需要手动处理，类型: varchar(20), 存储: VIRTUAL
-- 虚拟列 v_tireReplacementReason 需要手动处理，类型: varchar(500), 存储: VIRTUAL
-- 虚拟列 v_tireRemovalReason 需要手动处理，类型: varchar(500), 存储: VIRTUAL
-- 虚拟列 v_tireReplacementRemovalReason 需要手动处理，类型: varchar(500), 存储: VIRTUAL
-- 虚拟列 v_tirePosition 需要手动处理，类型: varchar(50), 存储: VIRTUAL
-- 虚拟列 v_tireNumber 需要手动处理，类型: varchar(50), 存储: VIRTUAL
-- 虚拟列 v_tirePositionChangeReason 需要手动处理，类型: varchar(50), 存储: VIRTUAL
-- 虚拟列 v_tirePositionChangeSuggestion 需要手动处理，类型: varchar(50), 存储: VIRTUAL
-- 虚拟列 v_tireInflationPosition 需要手动处理，类型: varchar(50), 存储: VIRTUAL
-- 虚拟列 v_tirePressure 需要手动处理，类型: varchar(50), 存储: VIRTUAL
-- 虚拟列 v_tireRemovalInstallationPosition 需要手动处理，类型: varchar(50), 存储: VIRTUAL
-- 虚拟列 v_tireInspectedVehicleCount 需要手动处理，类型: varchar(50), 存储: VIRTUAL
-- 虚拟列 v_tireIsSupplementaryOrder 需要手动处理，类型: smallint(6), 存储: VIRTUAL
-- 虚拟列 v_tireRepairTypeId 需要手动处理，类型: varchar(20), 存储: VIRTUAL
-- 虚拟列 v_tireRepairTypeName 需要手动处理，类型: varchar(20), 存储: VIRTUAL
-- 虚拟列 v_need_reinstall 需要手动处理，类型: varchar(50), 存储: VIRTUAL
-- 虚拟列 v_chpCarModel 需要手动处理，类型: varchar(50), 存储: VIRTUAL
-- 虚拟列 v_CustomerAuditStatus 需要手动处理，类型: int(11), 存储: VIRTUAL
-- 虚拟列 v_LastAddRecordTime 需要手动处理，类型: datetime, 存储: VIRTUAL
-- 虚拟列 v_Power 需要手动处理，类型: decimal(18,1), 存储: VIRTUAL
ALTER TABLE `tb_workgoodsinfo` ADD COLUMN `InstallResult` smallint(6) NULL   COMMENT '安装结果：0.安装失败；1.安装成功；';
ALTER TABLE `tb_workgoodsinfo` ADD COLUMN `InstallFailReason` varchar(200) NULL   COMMENT '安装失败原因';
ALTER TABLE `tb_workorderinfo` ADD COLUMN `CloseAt` datetime NULL   COMMENT '关闭时间';
ALTER TABLE `tb_workorderrelation` ADD COLUMN `RelateNo` varchar(50) NULL   COMMENT '关联关系编码';
ALTER TABLE `tb_workorderstatus` ADD COLUMN `SettleType` smallint(6) NULL   COMMENT '工单结算类型：0.不结算；1.现结；2.月结；3.周结；';
ALTER TABLE `tb_workresourceinfo` ADD COLUMN `IsOcrCheck` smallint(6) NULL   COMMENT 'OCR识别状态：0.未识别；1.已识别;';
ALTER TABLE `tb_workserviceinfo` ADD COLUMN `WorkerId` char(36) NULL   COMMENT '小工Id';
ALTER TABLE `tb_workserviceinfo` ADD COLUMN `WorkerCode` varchar(50) NULL   COMMENT '小工账号';
ALTER TABLE `tb_workserviceinfo` ADD COLUMN `WorkerName` varchar(50) NULL   COMMENT '小工姓名';
ALTER TABLE `tb_worksurveydetail` MODIFY COLUMN `DeviceVirtualCode` varchar(500) NULL   COMMENT '设备虚拟编码';
ALTER TABLE `tb_worksurveydetail` MODIFY COLUMN `DeviceNumber` varchar(500) NULL   COMMENT '设备唯一编码';
-- TEXT/BLOB类型字段 TempAssetName 变更需要手动处理，类型: text, 允许NULL: True, COMMENT '资产名称'
ALTER TABLE `tb_worksurveydetail` MODIFY COLUMN `TempAssetBrand` varchar(100) NULL   COMMENT '资产品牌';
-- TEXT/BLOB类型字段 TempAssetModel 变更需要手动处理，类型: text, 允许NULL: True, COMMENT '资产型号'
ALTER TABLE `tb_worksurveydetail` MODIFY COLUMN `TempAssetNumber` varchar(500) NULL   COMMENT '资产编号';
ALTER TABLE `tb_worksurveydetail` MODIFY COLUMN `TempAssetPlate` varchar(100) NULL   COMMENT '资产铭牌';
ALTER TABLE `tb_worksurveydetail` MODIFY COLUMN `FailReason` varchar(200) NULL   COMMENT '不合格原因';
ALTER TABLE `trans_customertag` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `workflowitems` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `workflownodeactions` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `workflownodeactors` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `workflownoderelatedactors` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `workflownodes` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';
ALTER TABLE `workflownodestepconditions` ADD COLUMN `LastUpdateTimeStamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT '数据变更时间戳';

