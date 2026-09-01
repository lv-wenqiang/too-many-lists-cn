# 让一切泛型化

我们在 Option 和 Box 上已经稍微接触过泛型了。不过到目前为止，我们一直
设法回避了声明任何真正对任意元素泛型的新类型。

事实证明这其实非常简单。我们现在就把所有类型都变成泛型的：

```rust ,ignore
pub struct List<T> {
    head: Link<T>,
}

type Link<T> = Option<Box<Node<T>>>;

struct Node<T> {
    elem: T,
    next: Link<T>,
}
```

你只要给所有东西都加上一点尖括号，代码突然就泛型了。当然，我们不能*只*做
这些，否则编译器会气疯的。


```text
> cargo test

error[E0107]: wrong number of type arguments: expected 1, found 0
  --> src/second.rs:14:6
   |
14 | impl List {
   |      ^^^^ expected 1 type argument

error[E0107]: wrong number of type arguments: expected 1, found 0
  --> src/second.rs:36:15
   |
36 | impl Drop for List {
   |               ^^^^ expected 1 type argument

```

问题相当清楚：我们还在念叨`List`这个东西，但它已经不再是个真实存在的类型了。
就像 Option 和 Box 一样，我们现在必须始终说`List<某个类型>`。

可是在这些 impl 里，我们该用哪个“某个类型”呢？和 List 一样，我们希望自己的
实现能对*所有*的 T 都管用。所以，就像 List 那样，我们也给`impl`加上尖括号：


```rust ,ignore
impl<T> List<T> {
    pub fn new() -> Self {
        List { head: None }
    }

    pub fn push(&mut self, elem: T) {
        let new_node = Box::new(Node {
            elem: elem,
            next: self.head.take(),
        });

        self.head = Some(new_node);
    }

    pub fn pop(&mut self) -> Option<T> {
        self.head.take().map(|node| {
            self.head = node.next;
            node.elem
        })
    }
}

impl<T> Drop for List<T> {
    fn drop(&mut self) {
        let mut cur_link = self.head.take();
        while let Some(mut boxed_node) = cur_link {
            cur_link = boxed_node.next.take();
        }
    }
}
```

……就这样搞定了！


```text
> cargo test

     Running target/debug/lists-5c71138492ad4b4a

running 2 tests
test first::test::basics ... ok
test second::test::basics ... ok

test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured

```

现在我们所有的代码都对任意的 T 完全泛型了。哎呀，Rust 真是*简单*。
我想特别点名表扬一下`new`，它压根就没变过：

```rust ,ignore
pub fn new() -> Self {
    List { head: None }
}
```

尽情沐浴在 Self 的荣光之中吧，它是重构与复制粘贴式编程的守护神。
另一个有意思的点是，我们在构造 list 的实例时并没有写`List<T>`。
那部分是编译器替我们推导出来的，依据是我们要把它从一个期望返回`List<T>`的
函数里返回出去。

好了，我们继续，去看看全新的*行为*！
