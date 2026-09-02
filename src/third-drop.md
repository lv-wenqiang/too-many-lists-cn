# Drop（析构）

和可变链表一样，我们有递归析构函数的问题。
平心而论，对不可变链表来说这个问题没那么严重：如果我们碰到的某个节点是
*别处*另一个链表的头部，我们就不会递归地把它丢弃。不过这仍然是我们该关心的
事情，而且该怎么处理也没那么明显。下面是我们之前的解法：

```rust ,ignore
impl<T> Drop for List<T> {
    fn drop(&mut self) {
        let mut cur_link = self.head.take();
        while let Some(mut boxed_node) = cur_link {
            cur_link = boxed_node.next.take();
        }
    }
}
```

问题出在循环体上：

```rust ,ignore
cur_link = boxed_node.next.take();
```

这修改了 Box 内部的 Node，但用 Rc 我们做不到这一点；它只给我们共享访问权，
因为可能有任意多个其他的 Rc 正指向它。

但如果我们知道自己是最后一个知道这个节点的链表，那么把 Node 从 Rc 里移出来
*其实*是没问题的。这样我们也就知道该什么时候停下来：只要我们*没法*把 Node
提取出来，就停。

瞧啊，Rc 恰好有一个干这件事的方法：`try_unwrap`：

```rust ,ignore
impl<T> Drop for List<T> {
    fn drop(&mut self) {
        let mut head = self.head.take();
        while let Some(node) = head {
            if let Ok(mut node) = Rc::try_unwrap(node) {
                head = node.next.take();
            } else {
                break;
            }
        }
    }
}
```

```text
cargo test
   Compiling lists v0.1.0 (/Users/ADesires/dev/too-many-lists/lists)
    Finished dev [unoptimized + debuginfo] target(s) in 1.10s
     Running /Users/ADesires/dev/too-many-lists/lists/target/debug/deps/lists-86544f1d97438f1f

running 8 tests
test first::test::basics ... ok
test second::test::basics ... ok
test second::test::into_iter ... ok
test second::test::iter ... ok
test second::test::iter_mut ... ok
test second::test::peek ... ok
test third::test::basics ... ok
test third::test::iter ... ok

test result: ok. 8 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out
```

太好了！
不错。
