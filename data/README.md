# 数据集

当前使用东北大学 **NEU-CLS** 热轧带钢表面缺陷分类集：

- 1800 张 200×200 灰度图
- 6 类：crazing / inclusion / patches / pitted_surface / rolled_in_scale / scratches
- 每类 300 张

官方来源：Kechen Song, Northeastern University。

重新下载：

```bash
gdown 1NGlXT9sIaQpyxUoT6MLKm1Pr6x8oxOvc -O data/NEU-CLS.zip
unrar x data/NEU-CLS.zip data/NEU-CLS/
```
