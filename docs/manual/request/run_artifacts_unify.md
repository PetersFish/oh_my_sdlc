# 背景
目前run的json文件和handoffs相关的文件都比较散，没有集中管理，导致run归档的时候，json文件归档了，但handoffs相关的文件还是散落在run目录下

# 需求
将同一个run-id相关的文件都放到一个目录下面
- 推荐最终形态：

```
- active/<run-id>/run.json
- history/<run-id>/run.json
```
<!-- - 同\<run-id\>目录下放 plans/、handoffs/、logs/ -->