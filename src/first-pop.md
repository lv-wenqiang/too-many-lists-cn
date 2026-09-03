# 弹出（pop）

和`push`一样，`pop`想要改变列表；除此之外，我们还想返回结果。然而`pop`还得处理一个特殊的边界情况：如果列表是空的呢？为了表示这个情况，我们使用可靠的`Option`类型：

```rust ,ignore
pub fn pop(&mut self) -> Option<i32> {
    // TODO
}
```

`Option<T>`是一个表示一个值可能存在也可能不存在的enum。它要么是`Some(T)`，要么是`None`。我们也可以像Link一样创建一个自己的enum，但是我们想让用户了解我们的返回类型到底是什么，而Option是如此的无处不在，每个人都知道它。实际上，因为它是如此的基本，它被隐式的导入到了每一个源文件的作用域中，也包括它的两个变体：`Some`和`None`（这样我们就不用写`Option::None`）。

在`Option<T>`尖括号里的部分指出Option实际上是一个泛型，它的泛型参数是T。这意味着你可以创建一个任何类型的Option！

所以，我们有这个`Link`了，我们怎么检查它是Empty还是More呢？使用`match`进行模式匹配：

```rust ,ignore
pub fn pop(&mut self) -> Option<i32> {
    match self.head {
        Link::Empty => {
            // TODO
        }
        Link::More(node) => {
            // TODO
        }
    };
}
```

```text
> cargo build

error[E0308]: mismatched types
  --> src/first.rs:27:30
   |
27 |     pub fn pop(&mut self) -> Option<i32> {
   |            ---               ^^^^^^^^^^^ expected enum `std::option::Option`, found ()
   |            |
   |            this function's body doesn't return
   |
   = note: expected type `std::option::Option<i32>`
              found type `()`
```

啊，`pop` 必须返回一个值，我们还没做这件事。我们*可以*直接返回 `None`，但是在这种情况下，返回 `unimplemented!()` 来表明函数尚未实现会更好。`unimplemented!()` 是一个宏（`!` 表示宏），执行到它时会让程序 panic（基本上就是以受控方式崩溃）。

```rust ,ignore
pub fn pop(&mut self) -> Option<i32> {
    match self.head {
        Link::Empty => {
            // TODO
        }
        Link::More(node) => {
            // TODO
        }
    };
    unimplemented!()
}
```

无条件 panic 是一个[发散函数][diverging]的例子。发散函数永远不会返回调用者，因此可以用在期待任意类型值的地方。这里，`unimplemented!()` 被用来代替 `Option<T>` 类型的值。

注意到我们不需要在程序里写`return`。函数中的最后一个表达式也就隐式的成为它的返回值。这让我们可以更精炼的表达简单的逻辑。你也可以像C系语言一样，显式的`return`返回。

```text
> cargo build

error[E0507]: cannot move out of borrowed content
  --> src/first.rs:28:15
   |
28 |         match self.head {
   |               ^^^^^^^^^
   |               |
   |               cannot move out of borrowed content
   |               help: consider borrowing here: `&self.head`
...
32 |             Link::More(node) => {
   |                        ---- data moved here
   |
note: move occurs because `node` has type `std::boxed::Box<first::Node>`, which does not implement the `Copy` trait
  --> src/first.rs:32:24
   |
32 |             Link::More(node) => {
   |                        ^^^^
```

加上 `&self.head` 后，模式匹配取得的是共享引用，因此不会尝试移动 `self` 的内容。

```text
help: consider borrowing here: `&self.head`
```

Rust 建议我们给 `match` 加上引用来修复问题。来试试吧：

```rust ,ignore
pub fn pop(&mut self) -> Option<i32> {
    match &self.head {
        Link::Empty => {
            // TODO
        }
        Link::More(node) => {
            // TODO
        }
    };
    unimplemented!()
}
```

```text
> cargo build

warning: unused variable: `node`
  --> src/first.rs:32:24
   |
32 |             Link::More(node) => {
   |                        ^^^^ help: consider prefixing with an underscore: `_node`
   |
   = note: #[warn(unused_variables)] on by default

warning: field is never used: `elem`
  --> src/first.rs:13:5
   |
13 |     elem: i32,
   |     ^^^^^^^^^
   |
   = note: #[warn(dead_code)] on by default

warning: field is never used: `next`
  --> src/first.rs:14:5
   |
14 |     next: Link,
   |     ^^^^^^^^^^
```

好耶，又编译了！现在让我们搞清楚实现逻辑。我们要创建一个Option，所以要为这个预留一个变量。在Empty情况下要返回None，在More情况下需要返回`Some(i32)`，并且改变列表的head。来吧：

```rust ,ignore
pub fn pop(&mut self) -> Option<i32> {
    let result;
    match &self.head {
        Link::Empty => {
            result = None;
        }
        Link::More(node) => {
            result = Some(node.elem);
            self.head = node.next;
        }
    };
    result
}
```

```text
> cargo build
   Compiling lists v0.1.0 (/Users/ADesires/dev/temp/lists)
error[E0507]: cannot move out of borrowed content
  --> src/first.rs:35:29
   |
35 |                 self.head = node.next;
   |                             ^^^^^^^^^ cannot move out of borrowed content

```

*头*

*磕桌*

我们只有 `node` 的共享引用，却试图把值移出它。

我们应该后退一步，思考我们要做什么。我们想要：

* 检查列表是否为空。
* 如果是空的，返回None
* 如果是非空
    * 移除list头部
    * 移除该头部的`elem`
    * 将列表的head替换为`next`
    * 返回`Some(elem)`

关键在于我们想*移除*东西，这意味着要*按值*取得链表的头部。显然不能通过 `&self.head`
得到的共享引用做到。我们也“只有” `self` 的可变引用，所以移动东西的唯一办法就是
*替换它*。看来我们又要做 Empty 之舞了！来试试看：

```rust ,ignore
pub fn pop(&mut self) -> Option<i32> {
    let result;
    match mem::replace(&mut self.head, Link::Empty) {
        Link::Empty => {
            result = None;
        }
        Link::More(node) => {
            result = Some(node.elem);
            self.head = node.next;
        }
    };
    result
}
```

```text
cargo build

   Finished dev [unoptimized + debuginfo] target(s) in 0.22s
```

我 的 天 哪

它编译了，一个警告都没有！！！！！

这里我要给出我的优化提示了：我们现在返回的是result变量的值，但实际上根本不用这么做！就像一个函数的结果是它的最后一个表达式，每个代码块的结果也是它的最后一个表达式。通常我们使用分号来阻止这一行为，这会让代码块的值变成空元组（tuple）`()`。这实际上也是不声明返回值的函数——例如`push`——返回的。

因此，我们可以将`pop`修改为：

```rust ,ignore
pub fn pop(&mut self) -> Option<i32> {
    match mem::replace(&mut self.head, Link::Empty) {
        Link::Empty => None,
        Link::More(node) => {
            self.head = node.next;
            Some(node.elem)
        }
    }
}
```

这样更简洁，也更符合惯用写法。注意 Link::Empty 分支完全去掉了花括号，因为只需要计算
一个表达式。这是简单情况的漂亮简写。

```text
cargo build

   Finished dev [unoptimized + debuginfo] target(s) in 0.22s
```

不错，仍然有效！

[ownership]: first-ownership.html
[diverging]: https://doc.rust-lang.org/nightly/book/ch19-04-advanced-types.html#the-never-type-that-never-returns
