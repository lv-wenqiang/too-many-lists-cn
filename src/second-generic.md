# 使其全部通用

我们已经通过Option和Box对泛型做了一些介绍。但是，
到目前为止，我们已经设法避免声明任何实际上是泛型的新类型，
超越任意元素。

事实证明，这其实很简单。让我们将所有类型通用
现在雨下得很大

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

你只是让一切变得更加尖锐，突然你的代码
泛型。当然，我们不能*只是*这样做，否则编译器会
成为超级疯子。


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

问题很明显：我们正在谈论`List`的事情，但这不是
像Option和Box一样，我们现在总是不得不谈论
`List<Something>`.

但是，我们在所有这些暗示中使用的东西是什么？就像List一样，我们希望我们的
与*所有* T一起工作的实现。所以，就像List一样，让我们
`impl`s POINTY ：


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

就是这样！


```text
> cargo test

     Running target/debug/lists-5c71138492ad4b4a

running 2 tests
test first::test::basics ... ok
test second::test::basics ... ok

test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured

```

我们所有的代码现在都完全是T. Dang任意值的泛型，
生锈是*容易的*。我想特别向`new`大喊大叫，但`new`没有
甚至改变：

```rust ,ignore
pub fn new() -> Self {
    List { head: None }
}
```

沐浴在荣耀中，那就是自我，重构和复制意大利面编码的守护者。
同样有趣的是，当我们构造一个实例时，我们不编写`List<T>`
列表。该部分是根据我们退回它的事实为我们推断的
来自需要`List<T>`的函数。

好吧，让我们转向全新的*行为* ！
