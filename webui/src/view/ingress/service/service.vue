<template>
    <div>
        <Card>
            <Tables
                ref="tables"
                searchable
                border
                search-place="top"
                v-model="serviceList"
                :columns="columns"
                :pageSize="pageSize"
            >
            <span slot="handleTopButtons">
                <Button type="success" class="top-btn" @click="openAddModal()">创建服务</Button>
                <Button type="primary" class="top-btn" @click="loadServiceList(true)">刷新</Button>
            </span>
            </Tables>
        </Card>
        <Modal v-if="editForm" v-model="editModalVisible" :title="editForm.action === 'add' ? '创建服务' : '更新服务'" :mask-closable="false" @on-cancel="closeEditFormModal()" witdth="560">
            <Form ref="editForm" :model="editForm" :rules="editFormRule" :label-width="100">
                <Form-item v-if="editForm.action === 'add'" label="服务名：" prop="name" :rules="editFormRule.name">
                    <Input v-model.trim="editForm.name"></Input>
                </Form-item>
                <Form-item label="服务前端：" prop="servers"  :rules="editFormRule.servers">
                    <Input v-model.trim="editForm.servers" type="textarea" :rows="6"></Input>
                    <Tag color="green">格式：每行一组IP:Port</Tag>
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
import { getServiceList, applyService, deleteService } from "@/api/ingress";
import Tables from "_c/tables";
import { NAction } from "_c/cae";
import { nCopy } from "@/libs/util";

let defaultForm = {
    action: "add",
    name: "",
    servers: "",
};

let editFormRule = {
    name: [
        {
            required: true,
            type: "string",
            message: "请填写实例名",
            trigger: "blur",
        },
    ],
    servers: [
        {
            required: true,
            type: "string",
            message: "请填写实例描述",
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
                { title: "服务名", key: "name", sortable: true },
                {
                    title: "服务前端",
                    key: "servers",
                    render: (h, params) => {
                        return h(
                            "div",
                            {
                                style: {
                                    whiteSpace: "pre-wrap",
                                },
                            },
                            params.row.servers
                        );
                    },
                },
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
                                "更新服务"
                            ),
                            h(NAction, {
                                props: {
                                    nActions: action,
                                },
                                on: {
                                    goAction: (index) => {
                                        let theAction = action[index];
                                        this.$Modal.confirm({
                                            title: "服务操作",
                                            content: `确认${theAction.label}<span style="color:#eb2f96;">${params.row.name}</span>服务吗？`,
                                            onOk: () => {
                                                let key = theAction.key;
                                                if (key == "delete") {
                                                    this.onDeleteService(
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
            serviceList: [],
            //表单
            editModalVisible: false,
            editSubmitBtnLoading: false,
            editForm: nCopy(defaultForm),
            editFormRule: nCopy(editFormRule),
        };
    },
    methods: {
        loadServiceList(msg = false) {
            getServiceList()
                .then((res) => {
                    let list = [];
                    if (res.data.code == 200) {
                        for (let item of res.data.result) {
                            let servers = [];
                            for (let server of item.servers) {
                                servers.push(`${server.ip}:${server.port}`);
                            }
                            list.push({
                                name: item.name,
                                servers: servers.join("\n"),
                            });
                        }
                    }
                    this.serviceList = list;
                    if (msg) {
                        this.$Message.info(`成功加载${list.length}条记录`);
                    }
                })
                .catch((err) => {
                    console.log(err);
                    this.$Message.info(`加载失败,${err}`);
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
                    let servers = [];
                    for (let server of data.servers.split("\n")) {
                        let ep = server.split(":");
                        servers.push({
                            ip: ep[0],
                            port: ep[1],
                        });
                    }
                    let payload = {
                        name: data.name,
                        servers: servers,
                    };
                    applyService(payload)
                        .then((res) => {
                            let data = res.data;
                            if (data.code == 200) {
                                this.$Message.success(
                                    data.action === "add"
                                        ? "创建成功"
                                        : "更新成功"
                                );
                                this.loadServiceList();
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
                    this.editSubmitBtnLoading = false;
                    this.$Message.error("表单校验失败");
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

        onDeleteService(serviceName) {
            deleteService(serviceName)
                .then((res) => {
                    let data = res.data;
                    if (data.code == 200) {
                        this.$Message.info("删除成功");
                        this.loadServiceList();
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
        this.loadServiceList(true);
    },
};
</script>

<style lang="less">
.top-btn {
    margin-left: 2px;
}
</style>
