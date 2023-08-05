<template>
    <div>
        <Card>
            <Tables ref="tables" searchable border search-place="top" v-model="instanceList" :columns="columns"
                :pageSize="pageSize">
                <span slot="handleTopButtons">
                    <Button type="success" class="top-btn" @click="openAddModal()">创建实例</Button>
                    <Button type="primary" class="top-btn" @click="loadInstanceList(true)">刷新</Button>
                </span>
            </Tables>
        </Card>
        <Modal v-if="editForm" v-model="editModalVisible" :title="editForm.action === 'add' ? '创建实例' : '更新实例'"
            :mask-closable="false" @on-cancel="closeEditFormModal()" width="760">
            <Form ref="editForm" :model="editForm" :rules="editFormRule" :label-width="100">
                <Form-item v-if="editForm.action === 'add'" label="名称：" prop="name" :rules="editFormRule.name">
                    <Input v-model.trim="editForm.name"></Input>
                </Form-item>
                <Form-item label="描述：" prop="desc" :rules="editFormRule.desc">
                    <Input v-model.trim="editForm.desc"></Input>
                </Form-item>
                <Form-item v-if="editForm.action === 'add'" label="镜像：" prop="image" :rules="editFormRule.image">
                    <Select v-model="editForm.image" filterable>
                        <Option v-for="item in imageList" :value="item.name + ':' + item.tag" :key="item.name + ':' + item.tag">{{
                            item.name }}:{{ item.tag }}</Option>
                    </Select>
                </Form-item>
                <Form-item label="授权秘钥：" prop="authKeys" :rules="editFormRule.authKeys">
                    <Input v-model.trim="editForm.authKeys" type="textarea" :rows="8"></Input>
                </Form-item>
                <Form-item v-for="(item, index) in editForm.envs" :prop="'envs.' + index" :rules="editFormRule.envs"
                    :label="index == 0 ? '环境变量' : ''" :key="index" :show-message="false" style="margin-bottom: 14px;">
                    <Row v-if="editForm.action === 'add'">
                        <Col span="6" style="margin-right:8px">
                            <Input v-model.trim="item.key"></Input>
                        </Col>
                        <Col span="6" style="margin-right:8px">
                            <Input v-model.trim="item.value"></Input>
                        </Col>
                        <Col span="1">
                            <Button @click="onDeleteEnv(index)">删除</Button>
                        </Col>
                    </Row>
                    <Row v-if="editForm.action === 'update'">
                        <Col span="6" style="margin-right:8px">
                            <Input v-model.trim="item.key" readonly></Input>
                        </Col>
                        <Col span="6" style="margin-right:8px">
                            <Input v-model.trim="item.value" readonly></Input>
                        </Col>
                    </Row>
                </Form-item>
                <Form-Item v-if="editForm.action === 'add'">
                    <Row>
                        <Col span="10">
                        <Button type="dashed" long icon="md-add" @click="onAddEnv()">添加环境变量</Button>
                        </Col>
                    </Row>
                </Form-Item>
            </Form>

            <div slot="footer">
                <Button type="text" @click="closeEditFormModal()">取消</Button>
                <Button type="primary" @click="submitEditForm()" :loading="editSubmitBtnLoading">确定</Button>
            </div>
        </Modal>
        <Modal v-if="imageForm" v-model="imageModalVisible" title="创建镜像" :mask-closable="false"
            @on-cancel="closeImageFormModal()" width="760">
            <Form ref="imageForm" :model="imageForm" :rules="imageFormRule" :label-width="100">
                <Form-item label="名称：" prop="name" :rules="imageFormRule.name">
                    <Input v-model.trim="imageForm.name"></Input>
                </Form-item>
                <Form-item label="标签：" prop="tag" :rules="imageFormRule.tag">
                    <Input v-model.trim="imageForm.tag"></Input>
                </Form-item>
                <Form-item label="描述：" prop="comment" :rules="imageFormRule.comment">
                    <Input v-model.trim="imageForm.comment"></Input>
                </Form-item>
            </Form>

            <div slot="footer">
                <Button type="text" @click="closeImageFormModal()">取消</Button>
                <Button type="primary" @click="submitImageForm()" :loading="imageSubmitBtnLoading">确定</Button>
            </div>
        </Modal>
    </div>
</template>

<script>
import Vue from "vue";
import Tables from "_c/tables";
import {
    getInstanceList,
    getInstance,
    addInstance,
    updateInstance,
    actionInstance,
    imageInstance,
    delInstance,
} from "@/api/instance";
import { getImageList } from "@/api/image";
import { nCopy } from "@/libs/util";
import { NAction } from "_c/cae";

let defaultForm = {
    action: "add",
    id: -1,
    name: "",
    desc: "",
    image: "",
    authKeys: "",
    envs: [],
};

let defaultImageForm = {
    id: -1,
    name: "",
    tag: "",
    comment: "",
};

let imageFormRule = {
    name: [
        {
            required: true,
            type: "string",
            message: "请填写镜像名称",
            trigger: "blur",
        },
    ],
    tag: [
        {
            required: true,
            type: "string",
            message: "请填写镜像标签",
            trigger: "blur",
        },
    ],
    comment: [
        {
            required: true,
            type: "string",
            message: "请填写镜像描述",
            trigger: "blur",
        },
    ],
};

let addFormRule = {
    name: [
        {
            required: true,
            type: "string",
            message: "请填写实例名",
            trigger: "blur",
        },
    ],
    desc: [
        {
            required: true,
            type: "string",
            message: "请填写实例描述",
            trigger: "blur",
        },
    ],
    image: [
        {
            required: true,
            type: "string",
            message: "请填写镜像",
            trigger: "blur",
        },
    ],
    authKeys: [
        {
            required: true,
            type: "string",
            message: "请填写授权秘钥",
            trigger: "blur",
        },
    ],
    envs: [
        {
            type: "object",
            required: false,
            fields: {
                key: [{ type: "string", required: true, message: "请填写环境变量名", trigger: "blur" }],
                value: [{ type: "string", required: true, message: "请填写环境变量值", trigger: "blur" }],
            }
        }
    ],
};

let editFormRule = {
    desc: [
        {
            required: true,
            type: "string",
            message: "请填写实例描述",
            trigger: "blur",
        },
    ],
    authKeys: [
        {
            required: true,
            type: "string",
            message: "请填写授权秘钥",
            trigger: "blur",
        },
    ],
    envs: [
        {
            type: "object",
            required: false,
            fields: {
                key: [{ type: "string", required: true, message: "请填写环境变量名", trigger: "blur" }],
                value: [{ type: "string", required: true, message: "请填写环境变量值", trigger: "blur" }],
            }
        }
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
                { title: "实例名", key: "Name", sortable: true },
                { title: "IP", key: "IP" },
                {
                    title: "运行状态",
                    key: "Status",
                    render: (h, params) => {
                        let isRunning = params.row.Status === "running";
                        let color = isRunning ? "#19be6b" : "#ed4014";
                        return h(
                            "span",
                            {
                                props: {},
                                style: {
                                    color: color,
                                    fontWeight: "bold",
                                },
                            },
                            params.row.Status
                        );
                    },
                },
                {
                    title: "创建时间",
                    key: "Created",
                    render: (h, params) => {
                        return h(
                            "span",
                            Vue.filter("date")(params.row.Created)
                        );
                    },
                },
                {
                    title: "操作",
                    key: "Action",
                    render: (h, params) => {
                        let isRunning = params.row.Status === "running";
                        let action = [
                            {
                                key: "start",
                                label: "启动",
                                disabled: isRunning,
                            },
                            {
                                key: "stop",
                                label: "停止",
                                disabled: !isRunning,
                            },
                            {
                                key: "restart",
                                label: "重启",
                                disabled: !isRunning,
                            },
                            { key: "delete", label: "释放" },
                        ];
                        return h("div", [
                            h(
                                "Button",
                                {
                                    props: {
                                        type: "success",
                                        size: "small",
                                    },
                                    style: {
                                        marginRight: "5px",
                                    },
                                    on: {
                                        click: () => {
                                            this.onDetailInstance(
                                                params.row.Id
                                            );
                                        },
                                    },
                                },
                                "描述"
                            ),
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
                                            this.openUpdateModal(params.row.Id);
                                        },
                                    },
                                },
                                "更新配置"
                            ),
                            h(
                                "Button",
                                {
                                    props: {
                                        type: "warning",
                                        size: "small",
                                    },
                                    style: {
                                        marginRight: "5px",
                                    },
                                    on: {
                                        click: () => {
                                            this.openAddImageModal(
                                                params.row.Id
                                            );
                                        },
                                    },
                                },
                                "创建镜像"
                            ),
                            h(NAction, {
                                props: {
                                    nActions: action,
                                },
                                on: {
                                    goAction: (index) => {
                                        let theAction = action[index];
                                        this.$Modal.confirm({
                                            title: "实例操作",
                                            content: `确认${theAction.label}<span style="color:#eb2f96;">${params.row.Name}</span>实例吗？`,
                                            onOk: () => {
                                                let key = theAction.key;
                                                if (key == "delete") {
                                                    this.onDeleteInstance(
                                                        params.row.Id
                                                    );
                                                } else if (
                                                    key == "restart" ||
                                                    key == "start" ||
                                                    key == "stop"
                                                ) {
                                                    this.onActionInstance(
                                                        params.row.Id,
                                                        key
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
            instanceList: [],
            imageList: [],
            //表单
            editModalVisible: false,
            editSubmitBtnLoading: false,
            editForm: nCopy(defaultForm),
            editFormRule: addFormRule,
            //镜像表单
            imageModalVisible: false,
            imageSubmitBtnLoading: false,
            imageForm: nCopy(defaultImageForm),
            imageFormRule: imageFormRule,
        };
    },

    methods: {
        loadInstanceList(msg = false) {
            getInstanceList()
                .then((res) => {
                    let list = [];
                    if (res.data.code == 200) {
                        list = res.data.result;
                    }
                    this.instanceList = list;
                    if (msg) {
                        this.$Message.info(`成功加载${list.length}条记录`);
                    }
                })
                .catch((err) => {
                    console.log(err);
                    this.$Message.info(`加载失败,${err}`);
                });
        },

        loadImageList(msg = false) {
            getImageList()
                .then((res) => {
                    let list = [];
                    if (res.data.code == 200) {
                        list = res.data.result;
                    }
                    this.imageList = list;
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
            this.editFormRule = addFormRule;
        },

        submitEditForm() {
            this.editSubmitBtnLoading = true;
            this.$refs["editForm"].validate((valid) => {
                if (valid) {
                    if (this.editForm.action === "update") {
                        let data = nCopy(this.editForm);
                        let instanceId = data.id;
                        let payload = {
                            desc: data.desc,
                            auth_keys: `${data.authKeys}`.split("\n"),
                            envs: data.envs,
                        };
                        updateInstance(instanceId, payload)
                            .then((res) => {
                                let code = res.data.code;
                                if (code == 200) {
                                    this.editSubmitBtnLoading = false;
                                    this.$Message.success("更新成功");
                                    this.loadInstanceList();
                                    this.closeEditFormModal();
                                } else {
                                    this.$Message.error(
                                        `更新失败,${res.data.msg}`
                                    );
                                    this.editSubmitBtnLoading = false;
                                }
                            })
                            .catch((err) => {
                                console.log(err);
                                this.$Message.error(`更新失败,${err}`);
                                this.editSubmitBtnLoading = false;
                            });
                    } else {
                        let data = nCopy(this.editForm);
                        let payload = {
                            name: data.name,
                            desc: data.desc,
                            image: data.image,
                            auth_keys: `${data.authKeys}`.split("\n"),
                            envs: data.envs,
                        };
                        addInstance(payload)
                            .then((res) => {
                                let code = res.data.code;
                                if (code == 200) {
                                    this.editSubmitBtnLoading = false;
                                    this.$Message.success("创建成功");
                                    this.loadInstanceList();
                                    this.closeEditFormModal();
                                } else {
                                    this.$Message.error(
                                        `创建失败,${res.data.msg}`
                                    );
                                    this.editSubmitBtnLoading = false;
                                }
                            })
                            .catch((err) => {
                                console.log(err);
                                this.$Message.error(`创建失败,${err}`);
                                this.editSubmitBtnLoading = false;
                            });
                    }
                } else {
                    this.$Message.error("表单校验失败");
                    this.editSubmitBtnLoading = false;
                }
            });
        },

        openAddModal() {
            this.editFormRule = addFormRule;
            this.$refs["editForm"].resetFields();
            this.editForm = nCopy(defaultForm);
            this.editSubmitBtnLoading = false;
            this.editModalVisible = true;
        },

        openUpdateModal(instanceId) {
            getInstance(instanceId)
                .then((res) => {
                    this.editFormRule = editFormRule;
                    this.$refs["editForm"].resetFields();
                    let model = res.data.result.model;
                    if (!model.envs) {
                        model.envs = []
                    }
                    this.editForm = nCopy({
                        id: model.id,
                        desc: model.desc,
                        authKeys: model.auth_keys.join("\n"),
                        envs: model.envs,
                    });
                    console.log(this.editForm)
                    this.editForm.action = "update";
                    this.editSubmitBtnLoading = false;
                    this.editModalVisible = true;
                })
                .catch((err) => {
                    console.log(err);
                    this.$Message.error(`加载失败,${err}`);
                });
        },

        onDeleteInstance(instanceId) {
            delInstance(instanceId)
                .then((res) => {
                    let code = res.data.code;
                    if (code == 200) {
                        this.$Message.info("释放成功");
                        this.loadInstanceList();
                    } else {
                        this.$Message.error(`释放失败,${res.data.msg}`);
                    }
                })
                .catch((err) => {
                    console.log(err);
                    this.$Message.error(`释放失败,${err}`);
                });
        },

        onDetailInstance(instanceId) {
            getInstance(instanceId)
                .then((res) => {
                    let model = res.data.result.model;
                    this.$Modal.info({
                        title: "实例描述",
                        content: `${model.desc}`,
                    });
                })
                .catch((err) => {
                    console.log(err);
                    this.$Message.error(`加载失败,${err}`);
                });
        },

        onActionInstance(instanceId, action) {
            actionInstance(instanceId, action)
                .then((res) => {
                    let code = res.data.code;
                    if (code == 200) {
                        this.$Message.info("操作成功");
                        this.loadInstanceList();
                    } else {
                        this.$Message.error(`操作失败,${res.data.msg}`);
                    }
                })
                .catch((err) => {
                    console.log(err);
                    this.$Message.error(`加载失败,${err}`);
                });
        },

        onDeleteEnv(index) {
            this.editForm.envs.splice(index, 1)
        },

        onAddEnv() {
            this.editForm.envs.push({
                key: "",
                value: "",
            })
            console.log(this.editForm)
        },

        closeImageFormModal() {
            this.$refs["imageForm"].resetFields();
            this.imageModalVisible = false;
        },

        submitImageForm() {
            this.imageSubmitBtnLoading = true;
            this.$refs["imageForm"].validate((valid) => {
                if (valid) {
                    let data = nCopy(this.imageForm);
                    let instanceId = data.id;
                    let payload = {
                        repository: data.name,
                        tag: data.tag,
                        comment: data.comment,
                    };
                    imageInstance(instanceId, payload)
                        .then((res) => {
                            let code = res.data.code;
                            if (code == 200) {
                                this.imageSubmitBtnLoading = false;
                                this.$Message.success("创建镜像成功");
                                this.closeImageFormModal();
                            } else {
                                this.$Message.error(
                                    `创建镜像失败,${res.data.msg}`
                                );
                            }
                        })
                        .catch((err) => {
                            console.log(err);
                            this.$Message.error(`创建镜像失败,${err}`);
                        });
                } else {
                    this.$Message.error("表单校验失败");
                    this.imageSubmitBtnLoading = false;
                }
            });
        },

        openAddImageModal(instanceId) {
            this.$refs["imageForm"].resetFields();
            let form = nCopy(defaultImageForm);
            form.id = instanceId;
            this.imageForm = form;
            this.imageSubmitBtnLoading = false;
            this.imageModalVisible = true;
        },
    },
    mounted() {
        this.loadInstanceList(true);
        this.loadImageList(false);
    },
};
</script>

<style lang="less">
.top-btn {
    margin-left: 2px;
}
</style>
