import axios from '@/libs/api.request'


export const getServiceList = () => {
    return axios.request({
        url: "/api/ingress/service",
        method: 'get'
    })
}

export const applyService = (payload) => {
    return axios.request({
        url: "/api/ingress/service/apply",
        method: 'post',
        data: payload
    })
}

export const deleteService = (serviceName) => {
    return axios.request({
        url: `/api/ingress/service/${serviceName}`,
        method: 'delete'
    })
}


export const getRouterList = () => {
    return axios.request({
        url: "/api/ingress/router",
        method: 'get'
    })
}

export const applyRouter = (payload) => {
    return axios.request({
        url: "/api/ingress/router/apply",
        method: 'post',
        data: payload
    })
}

export const deleteRouter = (routerName) => {
    return axios.request({
        url: `/api/ingress/router/${routerName}`,
        method: 'delete'
    })
}