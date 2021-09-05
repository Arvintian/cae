import axios from '@/libs/api.request'


export const getImageList = () => {
    return axios.request({
        url: '/api/image/list',
        method: 'get'
    })
}

export const delImage = (name, tag) => {
    return axios.request({
        url: `/api/image/delete`,
        method: "put",
        data: {
            "repository": name,
            "tag": tag
        }
    })
}

export const addImage = (name, tag) => {
    return axios.request({
        url: `/api/image/create`,
        method: "post",
        data: {
            "repository": name,
            "tag": tag
        }
    })
}