# Drop（析构）

我们现在可以创建一个栈，压入元素，弹出元素，甚至确认了一切都可以正常的工作！

我们需要担心清理链表吗？严格来说，完全不用！和 C++ 一样，Rust 使用析构函数（destructor）自动清理
不再需要的资源。如果一个类型实现了叫做 Drop 的*trait*，它就有析构函数。trait 是 Rust
对接口的称呼。Drop trait 的接口如下：

```rust ,ignore
pub trait Drop {
    fn drop(&mut self);
}
```

基本上是这个意思：“当对象退出作用域的时候，我会给你清理事务的第二次机会”。

如果你的类型包含实现了 Drop 的其他类型，而你只是想调用它们的析构函数，就不必实际实现
Drop。对于 List 来说，它只需析构自己的头部，而这又可能继续析构一个 `Box<Node>`。
所有这些都会自动处理，只是有一个问题。

自动处理会很糟糕。

让我们考虑这个简单的列表。

```text
list -> A -> B -> C
```

当 `list` 被析构时，它会尝试析构 A，A 又会尝试析构 B，B 再尝试析构 C。有些人可能
已经正确地紧张起来了。这是递归代码，而递归代码可能耗尽栈空间！

有些人可能会想：“这显然是尾递归，任何像样的语言都会确保这种代码不会耗尽栈。”但
事实并非如此！为了理解原因，让我们像编译器一样，手动为 List 实现它必须执行的 Drop：

```rust ,ignore
impl Drop for List {
    fn drop(&mut self) {
        // NOTE: you can't actually explicitly call `drop` in real Rust code;
        // we're pretending to be the compiler!
        self.head.drop(); // tail recursive - good!
    }
}

impl Drop for Link {
    fn drop(&mut self) {
        match *self {
            Link::Empty => {} // Done!
            Link::More(ref mut boxed_node) => {
                boxed_node.drop(); // tail recursive - good!
            }
        }
    }
}

impl Drop for Box<Node> {
    fn drop(&mut self) {
        self.ptr.drop(); // uh oh, not tail recursive!
        deallocate(self.ptr);
    }
}

impl Drop for Node {
    fn drop(&mut self) {
        self.next.drop();
    }
}
```

我们不能在释放内存之后再析构 Box 的内容，所以没有办法以尾递归的方式进行析构！Box 必须先析构其中的内容，再释放其内存；因此，析构 Box 不是尾递归的，表面上的尾递归链仍然会不断增长栈。
因此，我们必须为 `List` 手动编写迭代式析构，把节点从 Box 中提取出来。

```rust ,ignore
impl Drop for List {
    fn drop(&mut self) {
        let mut cur_link = mem::replace(&mut self.head, Link::Empty);
        // `while let` == "do this thing until this pattern doesn't match"
        while let Link::More(mut boxed_node) = cur_link {
            cur_link = mem::replace(&mut boxed_node.next, Link::Empty);
            // boxed_node goes out of scope and gets dropped here;
            // but its Node's `next` field has been set to Link::Empty
            // so no unbounded recursion occurs.
        }
    }
}
```

```text
> cargo test

     Running target/debug/lists-5c71138492ad4b4a

running 1 test
test first::test::basics ... ok

test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured

```

棒极了！

----------------------

<span style="float:left">![Bonus](img/profbee.gif)</span>

## 过早优化专栏！

我们的 drop 实现其实和 `while let Some(_) = self.pop() { }` 非常相似，后者当然更简单。
它们有什么区别？一旦我们开始让链表存储整数以外的东西，会产生什么性能问题？

<details>
  <summary>点击展开答案</summary>

`pop` 返回 `Option<i32>`，而我们的实现只操作 Links（`Box<Node>`）。因此我们的实现只
移动节点的指针，而基于 pop 的实现会移动节点中存储的值。如果我们泛化链表，而有人用
它存储 VeryBigThingWithADropImpl（VBTWADI）的实例，这可能非常昂贵。Box 能够原地运行
其内容的 drop 实现，因此不会遇到这个问题。既然 VBTWADI *恰恰*是让链表比数组更值得
使用的那类东西，在这种情况下表现糟糕就有点令人失望了。

如果想兼得两种实现的优点，可以添加一个新方法 `fn pop_node(&mut self) -> Link`，再由
它整洁地派生出 `pop` 和 `drop`。

</details>
