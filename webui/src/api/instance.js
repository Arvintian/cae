import axios from '@/libs/api.request'


export const getInstanceList = () => {
    return axios.request({
        url: '/api/instance/list',
        method: 'get'
    })
}


export const getInstance = (instanceId) => {
    return axios.request({
        url: `/api/instance/info/${instanceId}`,
        method: "get"
    })
}

export const addInstance = (payload) => {
    return axios.request({
        url: "/api/instance/create",
        data: payload,
        method: "post"
    })
}

export const updateInstance = (instanceId, payload) => {
    return axios.request({
        url: `/api/instance/update/${instanceId}`,
        data: payload,
        method: "put"
    })
}

export const actionInstance = (instanceId, action) => {
    return axios.request({
        url: `/api/instance/action/${instanceId}`,
        data: {
            "action": action
        },
        method: "put"
    })
}

export const imageInstance = (instanceId, payload) => {
    return axios.request({
        url: `/api/instance/image/${instanceId}`,
        data: payload,
        method: "put"
    })
}

export const delInstance = (instanceId) => {
    return axios.request({
        url: `/api/instance/delete/${instanceId}`,
        method: "delete"
    })
}