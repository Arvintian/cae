<template>
    <div>
        <Card>
            <Tables
                ref="tables"
                searchable
                border
                search-place="top"
                v-model="imageList"
                :columns="columns"
                :pageSize="pageSize"
            >
            <span slot="handleTopButtons">
                <Button type="success" class="top-btn" @click="openAddModal()">添加镜像</Button>
                <Button type="primary" class="top-btn" @click="loadImageList(true)">刷新</Button>
            </span>
            </Tables>
        </Card>
        <Modal v-if="editForm" v-model="editModalVisible" title="创建镜像" :mask-closable="false" @on-cancel="closeEditFormModal()" witdth="560">
            <Form ref="editForm" :model="editForm" :rules="editFormRule" :label-width="100">
                <Form-item label="名称：" prop="repository" :rules="editFormRule.repository">
                    <Input v-model.trim="editForm.repository"></Input>
                </Form-item>
                <Form-item label="标签：" prop="tag" :rules="editFormRule.tag">
                    <Input v-model.trim="editForm.tag"></Input>
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
import Vue from "vue";
import { getImageList, delImage, addImage } from "@/api/image";
import Tables from "_c/tables";
import { NAction } from "_c/cae";
import { nCopy } from "@/libs/util";

let defaultForm = {
    repository: "",
    tag: "",
};

let editFormRule = {
    repository: [
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
};

export default {
    name: "instanceImage",
    components: {
        Tables,
        NAction,
    },
    data() {
        return {
            pageSize: 10,
            columns: [
                { title: "名称", key: "name", sortable: true },
                { title: "标签", key: "tag" },
                { title: "描述", key: "comment" },
                {
                    title: "ID",
                    key: "id",
                    render: (h, params) => {
                        return h(
                            "span",
                            params.row.id.split(":")[1].substring(0, 12)
                        );
                    },
                },
                {
                    title: "创建时间",
                    key: "created",
                    sortable: true,
                    render: (h, params) => {
                        return h(
                            "span",
                            Vue.filter("date")(params.row.created)
                        );
                    },
                },
                {
                    title: "操作",
                    key: "Action",
                    render: (h, params) => {
                        let action = [{ key: "delete", label: "删除" }];
                        return h(NAction, {
                            props: {
                                nActions: action,
                            },
                            on: {
                                goAction: (index) => {
                                    let theAction = action[index];
                                    this.$Modal.confirm({
                                        title: "镜像操作",
                                        content: `确认${theAction.label}<span style="color:#eb2f96;">${params.row.name}:${params.row.tag}</span>镜像吗？`,
                                        onOk: () => {
                                            let key = theAction.key;
                                            if (key == "delete") {
                                                this.onDeleteImage(
                                                    params.row.name,
                                                    params.row.tag
                                                );
                                            }
                                        },
                                    });
                                },
                            },
                        });
                    },
                },
            ],

            imageList: [],
            //表单
            editModalVisible: false,
            editSubmitBtnLoading: false,
            editForm: nCopy(defaultForm),
            editFormRule: nCopy(editFormRule),
        };
    },
    methods: {
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

        onDeleteImage(name, tag) {
            delImage(name, tag)
                .then((res) => {
                    let code = res.data.code;
                    if (code == 200) {
                        this.$Message.info("删除成功");
                        this.loadImageList();
                    } else {
                        this.$Message.error(`删除失败,${res.data.msg}`);
                    }
                })
                .catch((err) => {
                    console.log(err);
                    this.$Message.error(`删除失败,${err}`);
                });
        },

        openAddModal() {
            this.$refs["editForm"].resetFields();
            this.editForm = nCopy(defaultForm);
            this.editSubmitBtnLoading = false;
            this.editModalVisible = true;
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
                    console.log(data);
                    addImage(data.repository, data.tag)
                        .then((res) => {
                            let code = res.data.code;
                            if (code == 200) {
                                this.$Message.info("正在拉取镜像");
                                this.loadImageList();
                                this.closeEditFormModal();
                            } else {
                                this.$Message.error(`添加失败,${res.data.msg}`);
                            }
                        })
                        .catch((err) => {
                            console.log(err);
                            this.$Message.error(`删除失败,${err}`);
                        });
                } else {
                    this.editSubmitBtnLoading = false;
                    this.$Message.error("表单校验失败");
                }
            });
        },
    },
    mounted() {
        this.loadImageList(true);
    },
};
</script>

<style lang="less">
.top-btn {
    margin-left: 2px;
}
</style>
