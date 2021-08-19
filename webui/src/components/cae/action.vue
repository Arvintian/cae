<template>
    <Dropdown @on-click="goAction" transfer>
        <Button type="default" size="small">
            更多<Icon type="ios-arrow-down"></Icon>
        </Button>
        <DropdownMenu slot="list">
            <DropdownItem v-for="(action, index) in nActions" :key="index" :name="index" :disabled="action.disabled">
              {{action.label}}
            </DropdownItem>
        </DropdownMenu>
    </Dropdown>
</template>

<script>
/*
let action = [
  {
    key: 'aa',
    label: '水平扩展'
  }, {
    key: 'bb',
    label: '自动伸缩'
  }, {
    key: 'cc',
    label: '变更配置'
  }, {
    key: 'dd',
    label: '重新部署'
  }, {
    key: 'ee',
    label: '删除成功'
  }
]

return h(NAction, {
  props: {
    nActions: action
  },
  on: {
    goAction (index) {
      console.log(action[index])
    }
  }
})
*/
export default {
    name: "NAction",
    props: {
        nActions: {
            type: Array,
            required: true,
        },
    },
    watch: {},
    computed: {},
    data() {
        return {};
    },
    methods: {
        goAction(index) {
            if (!this.nActions[index].disabled) {
                this.$emit("goAction", +index);
            }
        },
    },
    created() {},
};
</script>
