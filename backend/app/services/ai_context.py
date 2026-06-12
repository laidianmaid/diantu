def build_shop_context(shops) -> str:
    return "\n".join(
        f"ID:{shop.id} 名称:{shop.name} 颜色:{shop.color} 地址:{shop.address} 状态:{shop.status.value} 风格:{shop.style or '未知'} 分数:{shop.score:.1f}"
        for shop in shops
    )
