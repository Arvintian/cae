<template>
    <div>
        <Card>
            <Tables
                ref="tables"
                searchable
                border
                search-place="top"
                v-model="routerList"
                :columns="columns"
                :pageSize="pageSize"
            >
            <span slot="handleTopButtons">
                <Button type="success" class="top-btn" @click="openAddModal()">创建路由</Button>
                <Button type="primary" class="top-btn" @click="loadRouterList(true)">刷新</Button>
            </span>
            </Tables>
        </Card>
        <Modal v-if="editForm" v-model="editModalVisible" :title="editForm.action === 'add' ? '创建路由' : '更新路由'" :mask-closable="false" @on-cancel="closeEditFormModal()" witdth="560">
            <Form ref="editForm" :model="editForm" :rules="editFormRule" :label-width="100">
                <Form-item v-if="editForm.action === 'add'" label="路由名：" prop="name" :rules="editFormRule.name">
                    <Input v-model.trim="editForm.name"></Input>
                </Form-item>
                <Form-item label="规则：" prop="rule"  :rules="editFormRule.rule">
                    <Input v-model.trim="editForm.rule"></Input>
                </Form-item>
                <Form-item label="服务组：" prop="service"  :rules="editFormRule.service">
                    <Select v-model="editForm.service">
                        <Option v-for="item in serviceList" :value="item.name" :key="item.name">{{ item.name }}</Option>
                    </Select>
                </Form-item>
            </Form>
            <div slot="footer">
                <Button type="text" @click="closeEditFormModal()">取消</Button>
                <Button type="primary" @click="submitEditForm()" :loading="editSubmitBtnLoading">确定</Button>
            </div>
        </Modal>
    </div>
</template>

<script>
import {
    getRouterList,
    applyRouter,
    deleteRouter,
    getServiceList,
} from "@/api/ingress";
import Tables from "_c/tables";
import { NAction } from "_c/cae";
import { nCopy } from "@/libs/util";

let defaultForm = {
    action: "add",
    name: "",
    rule: "",
    service: "",
};

let editFormRule = {
    name: [
        {
            required: true,
            type: "string",
            message: "请填写路由名",
            trigger: "blur",
        },
    ],
    rule: [
        {
            required: true,
            type: "string",
            message: "请填写路由规则",
            trigger: "blur",
        },
    ],
    service: [
        {
            required: true,
            type: "string",
            message: "请填写服务组",
            trigger: "blur",
        },
    ],
};

export default {
    name: "instance",
    components: {
        Tables,
        NAction,
    },
    data() {
        return {
            pageSize: 10,
            columns: [
                { title: "路由名", key: "name", sortable: true },
                { title: "规则", key: "rule" },
                { title: "服务组", key: "service" },
                {
                    title: "操作",
                    key: "Action",
                    render: (h, params) => {
                        let action = [{ key: "delete", label: "删除" }];
                        return h("div", [
                            h(
                                "Button",
                                {
                                    props: {
                                        type: "primary",
                                        size: "small",
                                    },
                                    style: {
                                        marginRight: "5px",
                                    },
                                    on: {
                                        click: () => {
                                            this.openUpdateModal(params.row);
                                        },
                                    },
                                },
                                "更新路由"
                            ),
                            h(NAction, {
                                props: {
                                    nActions: action,
                                },
                                on: {
                                    goAction: (index) => {
                                        let theAction = action[index];
                                        this.$Modal.confirm({
                                            title: "路由操作",
                                            content: `确认${theAction.label}<span style="color:#eb2f96;">${params.row.name}</span>路由吗？`,
                                            onOk: () => {
                                                let key = theAction.key;
                                                if (key == "delete") {
                                                    this.onDeleteRouter(
                                                        params.row.name
                                                    );
                                                }
                                            },
                                        });
                                    },
                                },
                            }),
                        ]);
                    },
                },
            ],
            routerList: [],
            serviceList: [],
            //表单
            editModalVisible: false,
            editSubmitBtnLoading: false,
            editForm: nCopy(defaultForm),
            editFormRule: nCopy(editFormRule),
        };
    },
    methods: {
        loadRouterList(msg = false) {
            getRouterList()
                .then((res) => {
                    let list = [];
                    if (res.data.code == 200) {
                        list = res.data.result;
                    }
                    this.routerList = list;
                    if (msg) {
                        this.$Message.info(`成功加载${list.length}条记录`);
                    }
                })
                .catch((err) => {
                    console.log(err);
                    this.$Message.info(`加载失败,${err}`);
                });
        },

        loadServiceList(msg = false) {
            getServiceList()
                .then((res) => {
                    let list = [];
                    if (res.data.code == 200) {
                        list = res.data.result;
                    }
                    this.serviceList = list;
                    if (msg) {
                        this.$Message.info(`成功加载服务${list.length}条记录`);
                    }
                })
                .catch((err) => {
                    console.log(err);
                    this.$Message.info(`加载服务失败,${err}`);
                });
        },

        closeEditFormModal() {
            this.$refs["editForm"].resetFields();
            this.editModalVisible = false;
        },

        submitEditForm() {
            this.editSubmitBtnLoading = true;
            this.$refs["editForm"].validate((valid) => {
                if (valid) {
                    let data = nCopy(this.editForm);
                    let payload = {
                        name: data.name,
                        rule: data.rule,
                        service: data.service,
                    };
                    applyRouter(payload)
                        .then((res) => {
                            let data = res.data;
                            if (data.code == 200) {
                                this.$Message.success(
                                    data.action === "add"
                                        ? "创建成功"
                                        : "更新成功"
                                );
                                this.loadRouterList();
                                this.closeEditFormModal();
                            } else {
                                this.$Message.error(
                                    data.action === "add"
                                        ? `创建失败:${data.msg}`
                                        : `更新失败:${data.msg}`
                                );
                            }
                        })
                        .catch((err) => {
                            console.log(err);
                            this.$Message.error(
                                data.action === "add" ? "创建失败" : "更新失败"
                            );
                        });
                } else {
                    this.$Message.error("表单校验失败");
                    this.editSubmitBtnLoading = false;
                }
            });
        },

        openAddModal() {
            this.$refs["editForm"].resetFields();
            this.editForm = nCopy(defaultForm);
            this.editSubmitBtnLoading = false;
            this.editModalVisible = true;
        },

        openUpdateModal(svc) {
            this.$refs["editForm"].resetFields();
            this.editForm = nCopy(svc);
            this.editForm.action = "update";
            this.editSubmitBtnLoading = false;
            this.editModalVisible = true;
        },

        onDeleteRouter(routerName) {
            deleteRouter(routerName)
                .then((res) => {
                    let data = res.data;
                    if (data.code == 200) {
                        this.$Message.info("删除成功");
                        this.loadRouterList();
                    } else {
                        this.$Message.error(`删除失败:${data.msg}`);
                    }
                })
                .catch((err) => {
                    console.log(err);
                    this.$Message.error("删除失败");
                });
        },
    },
    mounted() {
        this.loadRouterList(true);
        this.loadServiceList();
    },
};
</script>

<style lang="less">
.top-btn {
    margin-left: 2px;
}
</style>
