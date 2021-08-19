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
                <Button type="primary" class="top-btn" @click="loadImageList(true)">刷新</Button>
            </span>
            </Tables>
        </Card>
    </div>
</template>

<script>
import Vue from "vue";
import { getImageList, delImage } from "@/api/image";
import Tables from "_c/tables";
import { NAction } from "_c/cae";

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
                { title: "名称", key: "name", sortable: true },
                { title: "标签", key: "tag" },
                { title: "描述", key: "comment" },
                {
                    title: "创建时间",
                    key: "created",
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
